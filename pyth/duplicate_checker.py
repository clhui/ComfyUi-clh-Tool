#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 大文件重复检查节点
基于原有的 check_large_duplicates.py 功能，转换为 ComfyUI 自定义节点
支持扫描 ComfyUI 根目录和模型目录，查找重复的大文件
"""

import os
import hashlib
import sys
from datetime import datetime
from collections import defaultdict
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import json
import pickle
import tempfile
import atexit
import folder_paths

class LargeDuplicateChecker:
    """大文件重复检查器核心类"""
    
    def __init__(self, directory, min_size_mb=100, max_workers=None, enable_resume=True, model_files_only=False):
        self.directory = directory
        self.min_size_bytes = min_size_mb * 1024 * 1024  # 转换为字节
        self.file_hashes = defaultdict(list)
        self.processed_files = 0
        self.total_files = 0
        self.start_time = None
        
        # 文件类型过滤相关
        self.model_files_only = model_files_only
        self.model_extensions = {
            '.ckpt',        # Stable Diffusion checkpoints
            '.safetensors', # SafeTensors format
            '.pt',          # PyTorch models
            '.pth',         # PyTorch models
            '.bin',         # Binary model files
            '.pkl',         # Pickle files
            '.h5',          # HDF5 format
            '.pb',          # TensorFlow protobuf
            '.onnx',        # ONNX models
            '.tflite',      # TensorFlow Lite
            '.engine',      # TensorRT engine
            '.plan',        # TensorRT plan
            '.model',       # Generic model files
            '.weights',     # Weight files
        }
        
        # 断点续传相关
        self.enable_resume = enable_resume
        self.checkpoint_file = os.path.join(directory, f"duplicate_checker_{abs(hash(directory))}.checkpoint")
        self.processed_file_set = set()  # 已处理的文件集合
        self.scan_completed = False  # 扫描是否完成
        
        # 两阶段检测相关
        self.quick_hashes = defaultdict(list)  # 快速哈希结果
        self.quick_scan_completed = False  # 快速扫描是否完成
        self.full_verification_files = []  # 需要完整验证的文件列表
        
        # 优化线程配置：对于I/O密集型任务，使用更多线程
        if max_workers is None:
            cpu_count = multiprocessing.cpu_count() or 1
            # I/O密集型任务可以使用更多线程，通常是CPU核心数的2-4倍
            self.max_workers = min(64, cpu_count * 4)
        else:
            self.max_workers = max_workers
            
        self.lock = threading.Lock()  # 用于线程安全的计数器和日志
        
        # 添加性能监控
        self.io_start_time = None
        self.total_bytes_processed = 0
        
        # 日志收集器
        self.log_messages = []
        
        # 注册清理函数
        if self.enable_resume:
            atexit.register(self.cleanup_checkpoint)
    
    def log(self, message):
        """输出带时间戳的日志（线程安全）"""
        with self.lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                log_msg = f"[{timestamp}] {message}"
                self.log_messages.append(log_msg)
                print(log_msg)
            except UnicodeEncodeError:
                # 处理编码问题，移除emoji字符
                clean_message = message.encode('ascii', 'ignore').decode('ascii')
                log_msg = f"[{timestamp}] {clean_message}"
                self.log_messages.append(log_msg)
                print(log_msg)
            sys.stdout.flush()  # 强制刷新输出缓冲区
        
    def format_size(self, size_bytes):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def calculate_quick_hash(self, file_path, sample_size=1024*1024):
        """计算文件快速哈希值（只读取前1MB用于预筛选）"""
        hash_md5 = hashlib.md5()
        try:
            file_size = os.path.getsize(file_path)
            
            with open(file_path, "rb") as f:
                # 只读取文件开头的指定大小
                chunk = f.read(min(sample_size, file_size))
                hash_md5.update(chunk)
                # 将文件大小也加入哈希，确保不同大小的文件不会有相同的快速哈希
                hash_md5.update(str(file_size).encode())
                
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            self.log(f"❌ 快速哈希失败: {os.path.basename(file_path)} - {str(e)}")
            return None

    def calculate_md5(self, file_path):
        """计算文件的完整MD5哈希值"""
        hash_md5 = hashlib.md5()
        try:
            file_size = os.path.getsize(file_path)
            processed_bytes = 0
            
            filename = os.path.basename(file_path)
            self.log(f"🔄 计算完整MD5: {filename} ({self.format_size(file_size)})")
            
            with open(file_path, "rb") as f:
                # 使用更大的缓冲区提高I/O效率
                chunk_size = 1024 * 1024  # 1MB chunks for better performance
                last_progress_shown = 0
                
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    hash_md5.update(chunk)
                    processed_bytes += len(chunk)
                    
                    # 对于大文件，每20%显示一次进度，避免频繁输出
                    if file_size > 100 * 1024 * 1024:
                        progress = (processed_bytes / file_size) * 100
                        # 只在进度达到20%的倍数时显示，减少滚动
                        if progress >= last_progress_shown + 20:
                            last_progress_shown = int(progress // 20) * 20
                            self.log(f"📊 {filename} - {last_progress_shown}%")
                        
            result = hash_md5.hexdigest()
            self.log(f"✅ MD5计算完成: {filename} -> {result[:8]}...")
            return result
        except (IOError, OSError) as e:
            self.log(f"❌ 读取失败: {os.path.basename(file_path)} - {str(e)}")
            return None
    
    def scan_directory(self):
        """扫描目录，查找大文件"""
        self.log(f"🔍 开始扫描目录: {self.directory}")
        self.log(f"📏 最小文件大小阈值: {self.format_size(self.min_size_bytes)}")
        
        if self.model_files_only:
            self.log(f"🎯 仅扫描模型文件，支持的扩展名: {', '.join(sorted(self.model_extensions))}")
        
        large_files = []
        
        try:
            for root, dirs, files in os.walk(self.directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 如果启用了模型文件过滤，检查文件扩展名
                    if self.model_files_only:
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext not in self.model_extensions:
                            continue  # 跳过非模型文件
                    
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size >= self.min_size_bytes:
                            large_files.append((file_path, file_size))
                            file_type = "模型文件" if self.model_files_only else "大文件"
                            self.log(f"📄 发现{file_type}: {os.path.basename(file_path)} ({self.format_size(file_size)})")
                    except (OSError, IOError) as e:
                        self.log(f"⚠️  无法访问文件 {file_path}: {str(e)}")
                        continue
        except Exception as e:
            self.log(f"❌ 扫描目录出错: {str(e)}")
            return []
        
        self.total_files = len(large_files)
        self.scan_completed = True
        
        file_type_desc = "模型文件" if self.model_files_only else "大文件"
        self.log(f"📊 扫描完成，共发现 {self.total_files} 个{file_type_desc}")
        
        return large_files
    
    def find_duplicates_simple(self, large_files):
        """简化版重复文件检测，适合ComfyUI节点使用"""
        if not large_files:
            return {}
        
        self.log(f"🚀 开始检测重复文件 (使用 {min(self.max_workers, len(large_files))} 个线程)")
        self.io_start_time = time.time()
        
        # 使用线程池并行计算哈希
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.calculate_md5, file_path): (file_path, file_size)
                for file_path, file_size in large_files
            }
            
            # 收集结果
            for future in as_completed(future_to_file):
                file_path, file_size = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        self.file_hashes[file_hash].append((file_path, file_size))
                        self.processed_files += 1
                        self.total_bytes_processed += file_size
                        
                        # 显示进度
                        progress = (self.processed_files / self.total_files) * 100 if self.total_files > 0 else 0
                        if self.processed_files % 5 == 0:  # 每5个文件显示一次进度
                            elapsed_time = time.time() - self.io_start_time
                            if elapsed_time > 0:
                                io_speed = (self.total_bytes_processed / elapsed_time) / (1024 * 1024)  # MB/s
                                self.log(f"📁 进度: [{self.processed_files}/{self.total_files}] ({progress:.1f}%) | 速度: {io_speed:.1f} MB/s")
                        
                except Exception as e:
                    self.log(f"❌ 处理文件失败 {file_path}: {str(e)}")
        
        # 过滤出重复文件
        duplicates = {hash_val: files for hash_val, files in self.file_hashes.items() if len(files) > 1}
        
        return duplicates
    
    def cleanup_checkpoint(self):
        """清理检查点文件"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
        except Exception:
            pass  # 忽略清理错误


class CLHDuplicateChecker:
    """ComfyUI 大文件重复检查节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # 获取ComfyUI根目录
        try:
            comfyui_root = os.path.dirname(os.path.dirname(os.path.dirname(folder_paths.base_path)))
        except:
            comfyui_root = os.getcwd()
        
        # 获取模型目录
        models_dir = None
        try:
            # 获取ComfyUI的模型目录
            if hasattr(folder_paths, 'models_dir'):
                models_dir = folder_paths.models_dir
            else:
                # 尝试默认的models目录
                default_models_path = os.path.join(comfyui_root, "models")
                if os.path.exists(default_models_path):
                    models_dir = default_models_path
                    
        except Exception as e:
            print(f"获取模型目录失败: {e}")
        
        # 如果没有找到模型目录，使用ComfyUI根目录作为备选
        if not models_dir:
            models_dir = comfyui_root
        
        return {
            "required": {
                "min_size_mb": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 10000,
                    "step": 1,
                    "tooltip": "最小文件大小阈值(MB)"
                }),
                "model_files_only": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否只扫描模型文件"
                }),
                "max_workers": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 32,
                    "step": 1,
                    "tooltip": "最大并行线程数"
                }),
                "directory_type": (["ComfyUI根目录", "模型目录", "其他"], {
                    "default": "模型目录",
                    "tooltip": "选择要扫描的目录类型"
                }),
            },
            "optional": {
                "custom_directory": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "当选择'其他'时，输入自定义目录路径"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("duplicate_report", "log_output")
    FUNCTION = "check_duplicates"
    CATEGORY = "CLH Tool"
    DESCRIPTION = "检查指定目录下的重复大文件，支持模型文件过滤和多线程处理"
    
    def check_duplicates(self, min_size_mb, model_files_only, max_workers, directory_type, custom_directory=""):
        """执行重复文件检查"""
        
        # 根据directory_type确定扫描目录
        try:
            comfyui_root = os.path.dirname(os.path.dirname(os.path.dirname(folder_paths.base_path)))
        except:
            comfyui_root = os.getcwd()
        
        if directory_type == "ComfyUI根目录":
            scan_directory = comfyui_root
        elif directory_type == "模型目录":
            # 获取模型目录
            models_dir = None
            try:
                if hasattr(folder_paths, 'models_dir'):
                    models_dir = folder_paths.models_dir
                else:
                    # 尝试默认的models目录
                    default_models_path = os.path.join(comfyui_root, "models")
                    if os.path.exists(default_models_path):
                        models_dir = default_models_path
            except Exception as e:
                print(f"获取模型目录失败: {e}")
            
            # 如果没有找到模型目录，使用ComfyUI根目录作为备选
            if not models_dir:
                models_dir = comfyui_root
            
            scan_directory = models_dir
        else:  # 其他 - 使用自定义目录
            if not custom_directory or custom_directory.strip() == "":
                error_msg = "❌ 选择'其他'时必须提供自定义目录路径"
                return (error_msg, error_msg)
            
            scan_directory = custom_directory.strip()
        
        # 验证目录是否存在
        if not os.path.exists(scan_directory):
            error_msg = f"❌ 目录不存在: {scan_directory}"
            return (error_msg, error_msg)
        
        if not os.path.isdir(scan_directory):
            error_msg = f"❌ 路径不是目录: {scan_directory}"
            return (error_msg, error_msg)
        
        # 验证目录是否可访问
        try:
            os.listdir(scan_directory)
        except PermissionError:
            error_msg = f"❌ 没有权限访问目录: {scan_directory}"
            return (error_msg, error_msg)
        except Exception as e:
            error_msg = f"❌ 访问目录时出错: {scan_directory} - {str(e)}"
            return (error_msg, error_msg)
        
        try:
            # 创建重复文件检查器
            checker = LargeDuplicateChecker(
                directory=scan_directory,
                min_size_mb=min_size_mb,
                max_workers=max_workers,
                enable_resume=False,  # ComfyUI节点中禁用断点续传
                model_files_only=model_files_only
            )
            
            # 扫描目录
            large_files = checker.scan_directory()
            
            if not large_files:
                no_files_msg = f"✅ 在目录 {scan_directory} 中未发现符合条件的文件"
                return (no_files_msg, "\n".join(checker.log_messages))
            
            # 检测重复文件
            duplicates = checker.find_duplicates_simple(large_files)
            
            # 生成报告
            report_lines = []
            report_lines.append(f"🔍 重复文件检查报告")
            report_lines.append(f"📁 扫描目录: {scan_directory}")
            report_lines.append(f"📂 目录类型: {directory_type}")
            report_lines.append(f"📏 最小文件大小: {checker.format_size(checker.min_size_bytes)}")
            report_lines.append(f"🎯 仅模型文件: {'是' if model_files_only else '否'}")
            report_lines.append(f"📊 扫描文件总数: {len(large_files)}")
            report_lines.append(f"🔄 处理文件数: {checker.processed_files}")
            report_lines.append(f"💾 处理数据量: {checker.format_size(checker.total_bytes_processed)}")
            report_lines.append("")
            
            if duplicates:
                report_lines.append(f"⚠️  发现 {len(duplicates)} 组重复文件:")
                report_lines.append("")
                
                total_duplicate_size = 0
                total_duplicate_files = 0
                
                for i, (hash_val, files) in enumerate(duplicates.items(), 1):
                    files_size = files[0][1]  # 所有重复文件大小相同
                    duplicate_size = files_size * (len(files) - 1)  # 可节省的空间
                    total_duplicate_size += duplicate_size
                    total_duplicate_files += len(files)
                    
                    report_lines.append(f"📦 重复组 {i} (MD5: {hash_val[:8]}...)")
                    report_lines.append(f"   📏 文件大小: {checker.format_size(files_size)}")
                    report_lines.append(f"   🔢 重复数量: {len(files)} 个文件")
                    report_lines.append(f"   💾 可节省空间: {checker.format_size(duplicate_size)}")
                    report_lines.append("   📄 文件列表:")
                    
                    for file_path, file_size in files:
                        relative_path = os.path.relpath(file_path, scan_directory)
                        
                        # 获取文件创建时间
                        try:
                            creation_time = os.path.getctime(file_path)
                            creation_datetime = datetime.fromtimestamp(creation_time)
                            creation_str = creation_datetime.strftime("%Y-%m-%d %H:%M:%S")
                        except (OSError, ValueError) as e:
                            creation_str = "未知时间"
                        
                        report_lines.append(f"      - {relative_path} (创建时间: {creation_str})")
                    
                    report_lines.append("")
                
                report_lines.append("=" * 50)
                report_lines.append(f"📊 总计:")
                report_lines.append(f"   🔢 重复文件总数: {total_duplicate_files}")
                report_lines.append(f"   💾 可节省总空间: {checker.format_size(total_duplicate_size)}")
                
            else:
                report_lines.append("✅ 未发现重复文件")
            
            report = "\n".join(report_lines)
            log_output = "\n".join(checker.log_messages)
            
            return (report, log_output)
            
        except Exception as e:
            error_msg = f"❌ 检查过程中发生错误: {str(e)}"
            return (error_msg, error_msg)


# 节点类映射
NODE_CLASS_MAPPINGS = {
    "CLHDuplicateChecker": CLHDuplicateChecker,
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "CLHDuplicateChecker": "CLH 重复文件检查器",
}