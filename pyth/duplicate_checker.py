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
                # 注意：不包含文件大小在快速哈希中，这样内容相同的文件会有相同的快速哈希
                # 文件大小的比较会在后续的完整验证阶段进行
                
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            self.log(f"❌ 快速哈希失败: {os.path.basename(file_path)} - {str(e)}")
            return None

    def calculate_md5(self, file_path):
        """计算文件的MD5哈希值"""
        filename = os.path.basename(file_path)
        self.log(f"🔍 计算MD5: {filename}")
        
        try:
            hash_md5 = hashlib.md5()
            file_size = os.path.getsize(file_path)
            processed_bytes = 0
            last_progress_shown = 0
            
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
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
    
    def process_quick_scan(self, file_info):
        """第一阶段：快速扫描文件（只计算前1MB哈希）"""
        file_path, file_size = file_info
        
        # 获取线程ID用于调试
        thread_id = threading.get_ident() % 10000
        
        # 检查是否已经处理过
        if file_path in self.processed_file_set:
            self.log(f"[T-{thread_id}] ⏭️  跳过已处理文件: {os.path.basename(file_path)}")
            return True
        
        try:
            # 计算快速哈希
            quick_hash = self.calculate_quick_hash(file_path)
            
            if quick_hash:
                # 线程安全地更新共享数据
                with self.lock:
                    self.quick_hashes[quick_hash].append((file_path, file_size))
                    self.processed_files += 1
                    self.processed_file_set.add(file_path)
                    
                    # 计算进度百分比
                    progress = (self.processed_files / self.total_files) * 100 if self.total_files > 0 else 0
                    
                    # 每处理20个文件显示一次进度
                    if self.processed_files % 20 == 0:
                        progress_msg = f"[快速扫描] [{self.processed_files:3d}/{self.total_files:3d}] ({progress:5.1f}%) ⚡ {os.path.basename(file_path):<30}"
                        should_log = True
                    else:
                        should_log = False
                        progress_msg = None
                
                # 在锁外输出日志
                if should_log:
                    self.log(progress_msg)
                
                return True
            else:
                self.log(f"[T-{thread_id}] ❌ 快速哈希计算失败: {file_path}")
                return False
                
        except Exception as e:
            self.log(f"[T-{thread_id}] ❌ 快速扫描出错 {file_path}: {str(e)}")
            return False

    def process_full_verification(self, file_info):
        """第二阶段：完整验证文件（计算完整MD5哈希）"""
        file_path, file_size = file_info
        
        # 获取线程ID用于调试
        thread_id = threading.get_ident() % 10000
        
        try:
            self.log(f"[T-{thread_id}] 🔍 完整验证: {os.path.basename(file_path)}")
            
            # 计算完整哈希
            full_hash = self.calculate_md5(file_path)
            
            if full_hash:
                # 线程安全地更新共享数据
                with self.lock:
                    self.file_hashes[full_hash].append((file_path, file_size))
                    self.total_bytes_processed += file_size
                
                return True
            else:
                self.log(f"[T-{thread_id}] ❌ 完整哈希计算失败: {file_path}")
                return False
                
        except Exception as e:
            self.log(f"[T-{thread_id}] ❌ 完整验证出错 {file_path}: {str(e)}")
            return False

    def process_files_two_phase(self, large_files):
        """两阶段并行处理文件：先快速扫描，再完整验证"""
        self.log(f"🚀 开始两阶段处理文件 (使用 {self.max_workers} 个线程)")
        self.log(f"📊 待处理文件总数: {len(large_files)} 个")
        
        # 重置processed_files计数器
        self.processed_files = 0
        
        # 过滤出未处理的文件
        unprocessed_files = [(path, size) for path, size in large_files 
                           if path not in self.processed_file_set]
        
        if not unprocessed_files:
            self.log("✅ 所有文件都已处理完成")
            return
        
        self.log(f"🔄 需要处理的文件: {len(unprocessed_files)} 个")
        self.log(f"⏭️  已跳过的文件: {len(large_files) - len(unprocessed_files)} 个")
        
        # 第一阶段：快速扫描
        self.log("─" * 40)
        self.log("🔍 第一阶段：快速扫描 (只读取前1MB)")
        self.log("─" * 40)
        
        start_time = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交快速扫描任务
                future_to_file = {}
                for file_info in unprocessed_files:
                    future = executor.submit(self.process_quick_scan, file_info)
                    future_to_file[future] = file_info
                
                # 等待快速扫描完成
                quick_scan_success = 0
                for future in as_completed(future_to_file):
                    try:
                        result = future.result(timeout=30)
                        if result:
                            quick_scan_success += 1
                    except Exception as e:
                        file_info = future_to_file[future]
                        self.log(f"❌ 快速扫描异常 {os.path.basename(file_info[0])}: {str(e)}")
        
        except KeyboardInterrupt:
            self.log("⚠️  用户中断快速扫描")
            return
        
        quick_scan_time = time.time() - start_time
        self.log(f"✅ 快速扫描完成！耗时: {quick_scan_time:.2f} 秒，成功: {quick_scan_success} 个文件，生成 {len(self.quick_hashes)} 个不同哈希值")
        
        # 分析快速扫描结果，找出可能的重复文件
        self.log("🔍 分析快速扫描结果...")
        
        # 统计快速哈希分布
        single_file_hashes = 0
        duplicate_candidate_hashes = 0
        total_duplicate_candidates = 0
        
        for quick_hash, files in self.quick_hashes.items():
            if len(files) == 1:
                single_file_hashes += 1
            else:
                duplicate_candidate_hashes += 1
                total_duplicate_candidates += len(files)
        
        self.log(f"📋 快速哈希分布: 唯一文件 {single_file_hashes} 个，疑似重复 {duplicate_candidate_hashes} 个哈希值涉及 {total_duplicate_candidates} 个文件")
        
        potential_duplicate_paths = set()
        quick_hash_groups = {}  # 用于记录每个快速哈希对应的文件组
        
        for quick_hash, files in self.quick_hashes.items():
            if len(files) > 1:
                # 有多个文件具有相同的快速哈希，需要完整验证
                # files 是 (file_path, file_size) 元组的列表，需要提取文件路径
                file_paths = [file_info[0] for file_info in files]
                potential_duplicate_paths.update(file_paths)
                quick_hash_groups[quick_hash] = files
                file_names = [os.path.basename(path) for path in file_paths]
                self.log(f"⚠️  发现 {len(files)} 个文件具有相同快速哈希 {quick_hash[:8]}...: {', '.join(file_names)}")
        
        if not potential_duplicate_paths:
            self.log("🎉 快速扫描未发现潜在重复文件，无需完整验证！")
            return
        
        # 构建需要完整验证的文件信息列表
        potential_duplicates = [(path, size) for path, size in unprocessed_files 
                               if path in potential_duplicate_paths]
        
        # 第二阶段：完整验证
        self.log("─" * 40)
        self.log(f"🔍 第二阶段：完整验证 ({len(potential_duplicates)} 个文件)")
        self.log("💡 验证原因：这些文件在快速扫描中具有相同的哈希值，需要完整验证以确认是否真正重复")
        self.log("─" * 40)
        
        # 显示每个文件的验证原因
        for file_path, file_size in potential_duplicates:
            # 找到这个文件属于哪个快速哈希组
            for quick_hash, files in quick_hash_groups.items():
                if any(f[0] == file_path for f in files):
                    group_files = [os.path.basename(f[0]) for f in files]
                    self.log(f"🔍 {os.path.basename(file_path)} -> 与 {len(files)-1} 个文件快速哈希相同 ({quick_hash[:8]}...): {', '.join(group_files)}")
                    break
        
        verification_start = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交完整验证任务
                future_to_file = {}
                for file_info in potential_duplicates:
                    future = executor.submit(self.process_full_verification, file_info)
                    future_to_file[future] = file_info
                
                # 等待完整验证完成
                verification_success = 0
                for future in as_completed(future_to_file):
                    try:
                        result = future.result(timeout=300)  # 完整验证允许更长时间
                        if result:
                            verification_success += 1
                    except Exception as e:
                        file_info = future_to_file[future]
                        self.log(f"❌ 完整验证异常 {os.path.basename(file_info[0])}: {str(e)}")
        
        except KeyboardInterrupt:
            self.log("⚠️  用户中断完整验证")
            return
        
        verification_time = time.time() - verification_start
        total_time = time.time() - start_time
        
        self.log(f"✅ 完整验证完成！耗时: {verification_time:.2f} 秒，成功: {verification_success} 个文件")
        self.log("─" * 40)
        self.log(f"🎉 两阶段处理完成！总耗时: {total_time:.2f} 秒")
        self.log(f"⚡ 性能提升: 只需验证 {len(potential_duplicates)}/{len(unprocessed_files)} 个文件 ({len(potential_duplicates)/len(unprocessed_files)*100:.1f}%)")
        
        # 计算节省的时间
        estimated_full_scan_time = len(unprocessed_files) * (verification_time / max(1, len(potential_duplicates)))
        time_saved = estimated_full_scan_time - total_time
        if time_saved > 0:
            self.log(f"💰 预估节省时间: {time_saved:.1f} 秒 ({time_saved/estimated_full_scan_time*100:.1f}%)")

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
    
    def find_duplicates_two_phase(self, large_files):
        """两阶段重复文件检测，先快速扫描再完整验证"""
        if not large_files:
            return {}
        
        # 设置总文件数
        self.total_files = len(large_files)
        
        # 使用两阶段处理
        self.process_files_two_phase(large_files)
        
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


class CLHDuplicateChecker_clh:
    """ComfyUI 大文件重复检查节点"""
    
    @classmethod
    def INPUT_TYPES(cls):
        # 获取ComfyUI根目录
        try:
            comfyui_root = folder_paths.base_path
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
                    "multiline": True,
                    "tooltip": "当选择'其他'时，输入自定义目录路径（支持多个目录，每行一个）"
                }),
            }
        }
    
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("duplicate_report", "log_output")
    FUNCTION = "check_duplicates"
    CATEGORY = "CLH Tool"
    DESCRIPTION = "检查指定目录下的重复大模型文件，支持模型文件过滤和多线程处理"
    
    def check_duplicates(self, min_size_mb, model_files_only, max_workers, directory_type, custom_directory=""):
        """执行重复文件检查"""
        
        # 根据directory_type确定扫描目录
        try:
            comfyui_root = folder_paths.base_path
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
            
            # 处理多行目录输入，取第一个有效目录
            directories = [line.strip() for line in custom_directory.strip().split('\n') if line.strip()]
            if not directories:
                error_msg = "❌ 选择'其他'时必须提供至少一个有效的目录路径"
                return (error_msg, error_msg)
            
            scan_directory = directories[0]  # 使用第一个目录
            if len(directories) > 1:
                # 如果有多个目录，记录日志但只使用第一个
                print(f"⚠️  检测到多个目录，将使用第一个: {scan_directory}")
                print(f"   其他目录将被忽略: {', '.join(directories[1:])}")
        
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
            duplicates = checker.find_duplicates_two_phase(large_files)
            
            # 生成报告
            report_lines = []
            report_lines.append(f"🔍 重复大模型文件检测报告 - 📁 {scan_directory} | 📂 {directory_type} | 📏 {checker.format_size(checker.min_size_bytes)}+ | 🎯 {'仅模型' if model_files_only else '全部文件'}")
            report_lines.append(f"📊 扫描统计: {len(large_files)} 个文件 | 处理 {checker.processed_files} 个 | 数据量 {checker.format_size(checker.total_bytes_processed)}")
            report_lines.append("")
            
            if duplicates:
                report_lines.append(f"⚠️  发现 {len(duplicates)} 组重复大模型文件:")
                report_lines.append("")
                
                total_duplicate_size = 0
                total_duplicate_files = 0
                
                for i, (hash_val, files) in enumerate(duplicates.items(), 1):
                    files_size = files[0][1]  # 所有重复文件大小相同
                    duplicate_size = files_size * (len(files) - 1)  # 可节省的空间
                    total_duplicate_size += duplicate_size
                    total_duplicate_files += len(files)
                    
                    report_lines.append(f"📦 重复组 {i} (MD5: {hash_val[:8]}...) - 📏 {checker.format_size(files_size)} | 🔢 {len(files)} 个文件 | 💾 可节省 {checker.format_size(duplicate_size)}")
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
                report_lines.append(f"📊 总计: {total_duplicate_files} 个重复大模型文件 | 💾 可节省总空间: {checker.format_size(total_duplicate_size)}")
                
            else:
                report_lines.append("✅ 未发现重复大模型文件")
            
            report = "\n".join(report_lines)
            log_output = "\n".join(checker.log_messages)
            
            return (report, log_output)
            
        except Exception as e:
            error_msg = f"❌ 检查过程中发生错误: {str(e)}"
            return (error_msg, error_msg)


# 节点类映射
NODE_CLASS_MAPPINGS = {
    "duplicate_checker_clh": CLHDuplicateChecker_clh,
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "duplicate_checker_clh": "CLH 重复大模型文件检测",
}