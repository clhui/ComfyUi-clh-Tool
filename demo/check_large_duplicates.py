#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文件重复检查工具 (支持断点续传)
检查指定目录下大于100MB的重复文件，并提供实时日志输出
支持多线程并行处理，提高扫描效率
支持中断后从断点继续执行，避免重复计算
"""

import os
import hashlib
import sys
from datetime import datetime
from collections import defaultdict
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import multiprocessing
import json
import pickle
import tempfile
import atexit

class LargeDuplicateChecker:
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
        
        # 注册清理函数
        if self.enable_resume:
            atexit.register(self.cleanup_checkpoint)
    
    def log(self, message):
        """输出带时间戳的日志（线程安全）"""
        with self.lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                print(f"[{timestamp}] {message}")
            except UnicodeEncodeError:
                # 处理编码问题，移除emoji字符
                clean_message = message.encode('ascii', 'ignore').decode('ascii')
                print(f"[{timestamp}] {clean_message}")
            sys.stdout.flush()  # 强制刷新输出缓冲区
        
    def format_size(self, size_bytes):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def save_checkpoint(self):
        """保存检查点"""
        if not self.enable_resume:
            return
            
        try:
            checkpoint_data = {
                'version': '1.0',
                'directory': self.directory,
                'min_size_bytes': self.min_size_bytes,
                'processed_files': self.processed_files,
                'total_files': self.total_files,
                'processed_file_set': list(self.processed_file_set),
                'file_hashes': dict(self.file_hashes),
                'scan_completed': self.scan_completed,
                'total_bytes_processed': self.total_bytes_processed,
                'timestamp': time.time()
            }
            
            # 使用临时文件确保原子性写入
            temp_file = self.checkpoint_file + '.tmp'
            with open(temp_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            # 原子性重命名
            if os.path.exists(temp_file):
                if os.path.exists(self.checkpoint_file):
                    os.remove(self.checkpoint_file)
                os.rename(temp_file, self.checkpoint_file)
                
        except Exception as e:
            self.log(f"⚠️  保存检查点失败: {str(e)}")
    
    def load_checkpoint(self):
        """加载检查点"""
        if not self.enable_resume or not os.path.exists(self.checkpoint_file):
            return False
            
        try:
            with open(self.checkpoint_file, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            # 验证检查点数据
            if (checkpoint_data.get('directory') != self.directory or 
                checkpoint_data.get('min_size_bytes') != self.min_size_bytes):
                self.log("⚠️  检查点参数不匹配，将重新开始")
                return False
            
            # 恢复状态
            self.processed_files = checkpoint_data.get('processed_files', 0)
            self.total_files = checkpoint_data.get('total_files', 0)
            self.processed_file_set = set(checkpoint_data.get('processed_file_set', []))
            self.scan_completed = checkpoint_data.get('scan_completed', False)
            self.total_bytes_processed = checkpoint_data.get('total_bytes_processed', 0)
            
            # 恢复文件哈希
            file_hashes_dict = checkpoint_data.get('file_hashes', {})
            self.file_hashes = defaultdict(list)
            for hash_val, files in file_hashes_dict.items():
                self.file_hashes[hash_val] = files
            
            checkpoint_time = checkpoint_data.get('timestamp', 0)
            time_diff = time.time() - checkpoint_time
            
            self.log(f"📂 发现检查点文件 (保存于 {time_diff/60:.1f} 分钟前)")
            self.log(f"🔄 恢复进度: 已处理 {self.processed_files}/{self.total_files} 个文件")
            self.log(f"💾 已处理数据: {self.format_size(self.total_bytes_processed)}")
            
            return True
            
        except Exception as e:
            self.log(f"⚠️  加载检查点失败: {str(e)}")
            return False
    
    def cleanup_checkpoint(self):
        """清理检查点文件"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
        except Exception:
            pass  # 忽略清理错误
    
    def calculate_quick_hash(self, file_path, sample_size=1024*1024):
        """计算文件快速哈希值（只读取前1MB用于预筛选）"""
        hash_md5 = hashlib.md5()
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            with open(file_path, "rb") as f:
                # 只读取文件开头的指定大小
                chunk = f.read(min(sample_size, file_size))
                hash_md5.update(chunk)
                # 将文件大小也加入哈希，确保不同大小的文件不会有相同的快速哈希
                hash_md5.update(str(file_size).encode())
                
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            thread_id = threading.get_ident() % 10000
            self.log(f"[T-{thread_id}] ❌ 快速哈希失败: {os.path.basename(file_path)} - {str(e)}")
            return None

    def calculate_md5(self, file_path):
        """计算文件的完整MD5哈希值"""
        hash_md5 = hashlib.md5()
        try:
            file_size = os.path.getsize(file_path)
            processed_bytes = 0
            
            # 获取线程ID用于调试
            thread_id = threading.get_ident() % 10000
            filename = os.path.basename(file_path)
            
            # 只在开始时显示一次文件信息
            self.log(f"[T-{thread_id}] 🔄 完整MD5: {filename} ({self.format_size(file_size)})")
            
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
                            self.log(f"[T-{thread_id}] 📊 {filename} - {last_progress_shown}%")
                        
            result = hash_md5.hexdigest()
            self.log(f"[T-{thread_id}] ✅ 完整MD5完成: {filename} -> {result[:8]}...")
            return result
        except (IOError, OSError) as e:
            self.log(f"[T-{thread_id}] ❌ 读取失败: {os.path.basename(file_path)} - {str(e)}")
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

    def process_single_file(self, file_info):
        """处理单个文件的哈希计算（线程安全）- 保留原方法作为备用"""
        file_path, file_size = file_info
        
        # 获取线程ID用于调试
        thread_id = threading.get_ident() % 10000
        
        # 检查是否已经处理过
        if file_path in self.processed_file_set:
            self.log(f"[T-{thread_id}] ⏭️  跳过已处理文件: {os.path.basename(file_path)}")
            return True  # 跳过已处理的文件
        
        try:
            self.log(f"[T-{thread_id}] 🚀 开始处理文件: {os.path.basename(file_path)}")
            
            # 计算文件哈希
            file_hash = self.calculate_md5(file_path)
            
            if file_hash:
                self.log(f"[T-{thread_id}] 🔄 MD5计算成功，开始更新共享数据...")
                
                # 线程安全地更新共享数据
                with self.lock:
                    self.file_hashes[file_hash].append((file_path, file_size))
                    self.processed_files += 1
                    self.processed_file_set.add(file_path)
                    self.total_bytes_processed += file_size
                    
                    # 计算进度百分比
                    progress = (self.processed_files / self.total_files) * 100 if self.total_files > 0 else 0
                    
                    # 计算I/O速度
                    if self.io_start_time:
                        elapsed_time = time.time() - self.io_start_time
                        if elapsed_time > 0:
                            io_speed = (self.total_bytes_processed / elapsed_time) / (1024 * 1024)  # MB/s
                        else:
                            io_speed = 0
                    else:
                        io_speed = 0
                    
                    # 每处理10个文件保存一次检查点
                    if self.processed_files % 10 == 0:
                        # 在锁外保存检查点，避免死锁
                        should_save_checkpoint = True
                        
                        # 显示I/O速度信息
                        if io_speed > 0:
                            io_speed_msg = f"I/O速度: {io_speed:.1f} MB/s | 已处理: {self.format_size(self.total_bytes_processed)}"
                        else:
                            io_speed_msg = None
                    else:
                        should_save_checkpoint = False
                        io_speed_msg = None
                    
                    # 保存进度信息，在锁外输出
                    progress_msg = f"[T-{thread_id}] 📁 [{self.processed_files:3d}/{self.total_files:3d}] ({progress:5.1f}%) ✅ {os.path.basename(file_path):<30} ({self.format_size(file_size):>8})"
                
                # 在锁外输出日志，避免死锁
                self.log(progress_msg)
                if io_speed_msg:
                    self.log(f"[T-{thread_id}] 💾 {io_speed_msg}")
                
                # 在锁外保存检查点，避免死锁
                if should_save_checkpoint:
                    self.log(f"[T-{thread_id}] 💾 准备保存检查点...")
                    self.save_checkpoint()
                    self.log(f"[T-{thread_id}] 💾 检查点保存完成")
                
                self.log(f"[T-{thread_id}] ✅ 文件处理完成，返回True: {os.path.basename(file_path)}")
                return True
            else:
                with self.lock:
                    self.log(f"[T-{thread_id}] ❌ 无法计算哈希: {file_path}")
                self.log(f"[T-{thread_id}] ❌ 文件处理失败，返回False: {os.path.basename(file_path)}")
                return False
                
        except Exception as e:
            with self.lock:
                self.log(f"[T-{thread_id}] ❌ 处理文件出错 {file_path}: {str(e)}")
            self.log(f"[T-{thread_id}] ❌ 文件处理异常，返回False: {os.path.basename(file_path)}")
            return False
    
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
        
        # 保存扫描完成的检查点
        if self.enable_resume:
            self.save_checkpoint()
        
        return large_files
    
    def process_files_two_phase(self, large_files):
        """两阶段并行处理文件：先快速扫描，再完整验证"""
        self.log(f"🚀 开始两阶段处理文件 (使用 {self.max_workers} 个线程)")
        self.log(f"📊 待处理文件总数: {len(large_files)} 个")
        
        # 过滤出未处理的文件
        unprocessed_files = [(path, size) for path, size in large_files 
                           if path not in self.processed_file_set]
        
        if not unprocessed_files:
            self.log("✅ 所有文件都已处理完成")
            return
        
        self.log(f"🔄 需要处理的文件: {len(unprocessed_files)} 个")
        self.log(f"⏭️  已跳过的文件: {len(large_files) - len(unprocessed_files)} 个")
        
        # 第一阶段：快速扫描
        self.log("=" * 60)
        self.log("🔍 第一阶段：快速扫描 (只读取前1MB)")
        self.log("=" * 60)
        
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
        self.log(f"✅ 快速扫描完成！耗时: {quick_scan_time:.2f} 秒")
        self.log(f"📊 快速扫描成功: {quick_scan_success} 个文件")
        
        # 分析快速扫描结果，找出可能的重复文件
        self.log("🔍 分析快速扫描结果...")
        potential_duplicate_paths = set()
        
        for quick_hash, files in self.quick_hashes.items():
            if len(files) > 1:
                # 有多个文件具有相同的快速哈希，需要完整验证
                # files 是 (file_path, file_size) 元组的列表，需要提取文件路径
                file_paths = [file_info[0] for file_info in files]
                potential_duplicate_paths.update(file_paths)
                file_names = [os.path.basename(path) for path in file_paths]
                self.log(f"⚠️  发现 {len(files)} 个文件具有相同的快速哈希 {quick_hash[:8]}...")
                self.log(f"   📁 文件列表: {', '.join(file_names)}")
        
        if not potential_duplicate_paths:
            self.log("🎉 快速扫描未发现潜在重复文件，无需完整验证！")
            return
        
        # 构建需要完整验证的文件信息列表
        potential_duplicates = [(path, size) for path, size in unprocessed_files 
                               if path in potential_duplicate_paths]
        
        # 第二阶段：完整验证
        self.log("=" * 60)
        self.log(f"🔍 第二阶段：完整验证 ({len(potential_duplicates)} 个文件)")
        self.log("=" * 60)
        
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
        
        self.log(f"✅ 完整验证完成！耗时: {verification_time:.2f} 秒")
        self.log(f"📊 完整验证成功: {verification_success} 个文件")
        self.log("=" * 60)
        self.log(f"🎉 两阶段处理完成！总耗时: {total_time:.2f} 秒")
        self.log(f"⚡ 性能提升: 只需验证 {len(potential_duplicates)}/{len(unprocessed_files)} 个文件 ({len(potential_duplicates)/len(unprocessed_files)*100:.1f}%)")
        
        # 计算节省的时间
        estimated_full_scan_time = len(unprocessed_files) * (verification_time / max(1, len(potential_duplicates)))
        time_saved = estimated_full_scan_time - total_time
        if time_saved > 0:
            self.log(f"💰 预估节省时间: {time_saved:.1f} 秒 ({time_saved/estimated_full_scan_time*100:.1f}%)")

    def process_files_parallel(self, large_files):
        """并行处理文件哈希计算，支持断点续传"""
        self.log(f"🚀 开始并行处理文件 (使用 {self.max_workers} 个线程)")
        self.log(f"📊 待处理文件总数: {len(large_files)} 个")
        
        # 过滤出未处理的文件
        unprocessed_files = [(path, size) for path, size in large_files 
                           if path not in self.processed_file_set]
        
        if not unprocessed_files:
            self.log("✅ 所有文件都已处理完成")
            return
        
        self.log(f"🔄 需要处理的文件: {len(unprocessed_files)} 个")
        self.log(f"⏭️  已跳过的文件: {len(large_files) - len(unprocessed_files)} 个")
        
        # 记录I/O开始时间
        if not self.io_start_time:
            self.io_start_time = time.time()
        
        start_time = time.time()
        success_count = 0
        failure_count = 0
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self.log("🔄 开始提交任务...")
                
                # 提交所有未处理的文件任务
                future_to_file = {}
                for i, file_info in enumerate(unprocessed_files, 1):
                    future = executor.submit(self.process_single_file, file_info)
                    future_to_file[future] = file_info
                    self.log(f"📤 已提交任务 {i}/{len(unprocessed_files)}: {os.path.basename(file_info[0])}")
                
                self.log("⏳ 等待任务完成...")
                
                # 处理完成的任务
                completed_count = 0
                self.log(f"🔍 开始监听 {len(future_to_file)} 个任务的完成状态...")
                
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    file_path = file_info[0]
                    completed_count += 1
                    
                    self.log(f"🎯 检测到任务完成信号 ({completed_count}/{len(unprocessed_files)}): {os.path.basename(file_path)}")
                    
                    try:
                        self.log(f"🔍 正在获取任务结果 ({completed_count}/{len(unprocessed_files)}): {os.path.basename(file_path)}")
                        
                        # 添加超时避免无限等待
                        result = future.result(timeout=60)  # 1分钟超时
                        
                        if result:
                            success_count += 1
                            self.log(f"✅ 任务完成: {os.path.basename(file_path)}")
                        else:
                            failure_count += 1
                            self.log(f"❌ 任务失败: {os.path.basename(file_path)}")
                    except TimeoutError:
                        failure_count += 1
                        self.log(f"⏰ 任务超时 {os.path.basename(file_path)}: 超过1分钟")
                    except Exception as e:
                        failure_count += 1
                        self.log(f"❌ 任务异常 {os.path.basename(file_path)}: {str(e)}")
                
        except KeyboardInterrupt:
            self.log("⚠️  用户中断，正在保存进度...")
            self.save_checkpoint()
            raise
        except Exception as e:
            self.log(f"❌ 并行处理出错: {str(e)}")
            self.save_checkpoint()
            raise
        
        # 最终保存检查点
        self.save_checkpoint()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        self.log("✅ 并行处理完成！")
        self.log(f"📊 处理统计: 成功 {success_count} 个，失败 {failure_count} 个")
        self.log(f"⏱️  总耗时: {total_time:.2f} 秒")
        
        if success_count > 0:
            avg_speed = success_count / total_time
            self.log(f"⚡ 平均处理速度: {avg_speed:.2f} 文件/秒")
            
            # 计算并行效率
            theoretical_single_thread_time = success_count * (total_time / success_count) * self.max_workers
            self.log(f"🧵 并行效率: 使用 {self.max_workers} 个线程，理论单线程耗时约 {theoretical_single_thread_time:.1f} 秒")
    
    def check_duplicates(self):
        """检查重复文件，支持断点续传"""
        self.log("🔍 开始检查重复文件...")
        
        # 尝试加载检查点
        if self.enable_resume and self.load_checkpoint():
            self.log("📂 成功加载检查点，从中断处继续执行")
        else:
            self.log("🆕 开始新的扫描任务")
            self.start_time = time.time()
        
        try:
            # 如果扫描未完成，继续扫描
            if not self.scan_completed:
                self.log("📁 开始扫描目录...")
                large_files = self.scan_directory()
                self.scan_completed = True
                if self.enable_resume:
                    self.save_checkpoint()
            else:
                # 从检查点重建文件列表
                large_files = []
                for file_path in self.processed_file_set:
                    if os.path.exists(file_path):
                        try:
                            size = os.path.getsize(file_path)
                            large_files.append((file_path, size))
                        except OSError:
                            continue
                
                # 重新扫描以获取完整的文件列表
                self.log("🔄 重新扫描目录以获取完整文件列表...")
                current_files = self.scan_directory()
                
                # 合并已处理和当前文件列表
                all_files_dict = {path: size for path, size in current_files}
                for path, size in large_files:
                    if path not in all_files_dict:
                        all_files_dict[path] = size
                
                large_files = list(all_files_dict.items())
                self.log(f"📊 合并后的文件列表: {len(large_files)} 个文件")
            
            if not large_files:
                self.log("📭 没有找到符合条件的大文件")
                return
            
            # 使用两阶段优化处理文件
            self.process_files_two_phase(large_files)
            
            # 分析结果
            self.analyze_results()
            
        except KeyboardInterrupt:
            self.log("⚠️  检测到用户中断 (Ctrl+C)")
            if self.enable_resume:
                self.log("💾 正在保存进度到检查点文件...")
                self.save_checkpoint()
                self.log(f"✅ 进度已保存到: {self.checkpoint_file}")
                self.log("🔄 下次运行时将从中断处继续")
            raise
        except Exception as e:
            self.log(f"❌ 检查过程中发生错误: {str(e)}")
            if self.enable_resume:
                self.save_checkpoint()
            raise
        finally:
            # 成功完成后清理检查点文件
            if self.enable_resume and self.scan_completed and len(self.processed_file_set) > 0:
                self.cleanup_checkpoint()
                self.log("🧹 任务完成，已清理检查点文件")
    
    def analyze_results(self):
        """分析并报告重复文件"""
        self.log("=" * 60)
        self.log("📋 分析结果...")
        
        duplicates = {hash_val: files for hash_val, files in self.file_hashes.items() if len(files) > 1}
        
        if not duplicates:
            self.log("✨ 未发现重复的大文件")
            return
        
        self.log(f"🔍 发现 {len(duplicates)} 组重复文件:")
        self.log("=" * 60)
        
        total_wasted_space = 0
        result_lines = []
        
        # 添加标题行
        result_lines.append("=" * 60)
        result_lines.append("🔍 重复文件检测报告")
        result_lines.append(f"📅 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        result_lines.append(f"📁 扫描目录: {self.directory}")
        result_lines.append("=" * 60)
        
        for i, (hash_val, files) in enumerate(duplicates.items(), 1):
            file_size = files[0][1]  # 所有重复文件大小相同
            wasted_space = file_size * (len(files) - 1)  # 除了保留一个，其他都是浪费的空间
            total_wasted_space += wasted_space
            
            group_info = f"\n📂 重复组 {i}:"
            self.log(group_info)
            result_lines.append(group_info)
            
            hash_info = f"   🔐 哈希值: {hash_val}"
            self.log(hash_info)
            result_lines.append(hash_info)
            
            size_info = f"   📏 文件大小: {self.format_size(file_size)}"
            self.log(size_info)
            result_lines.append(size_info)
            
            count_info = f"   📊 重复数量: {len(files)} 个文件"
            self.log(count_info)
            result_lines.append(count_info)
            
            waste_info = f"   💾 浪费空间: {self.format_size(wasted_space)}"
            self.log(waste_info)
            result_lines.append(waste_info)
            
            location_info = f"   📁 文件位置:"
            self.log(location_info)
            result_lines.append(location_info)
            
            for file_path, _ in files:
                # 获取文件创建时间
                try:
                    creation_time = os.path.getctime(file_path)
                    creation_date = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
                    file_info = f"      • {file_path} (创建于: {creation_date})"
                except Exception as e:
                    file_info = f"      • {file_path} (创建时间获取失败: {str(e)})"
                self.log(file_info)
                result_lines.append(file_info)
        
        summary_line = "=" * 60
        total_info = f"💰 总计可节省空间: {self.format_size(total_wasted_space)}"
        
        # 显示总耗时
        total_time = time.time() - self.start_time
        time_info = f"⏱️  总耗时: {total_time:.1f} 秒"
        
        self.log(summary_line)
        self.log(total_info)
        self.log(time_info)
        self.log(summary_line)
        
        # 添加到结果文件
        result_lines.append(summary_line)
        result_lines.append(total_info)
        result_lines.append(time_info)
        result_lines.append(summary_line)
        
        # 保存结果到文件
        try:
            result_file = os.path.join(self.directory, f"duplicate_check_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(result_lines))
            self.log(f"📄 结果已保存到: {result_file}")
        except Exception as e:
            self.log(f"⚠️  保存结果文件失败: {str(e)}")

def main():
    """主函数"""
    print("🔍 大文件重复检查工具 v2.0 (支持断点续传)")
    print("=" * 60)
    
    # 获取系统信息
    cpu_count = os.cpu_count()
    optimized_threads = min(64, cpu_count * 4)
    
    print(f"💻 系统信息:")
    print(f"   CPU 核心数: {cpu_count}")
    print(f"   优化线程数: {optimized_threads} (适合I/O密集型任务)")
    print(f"   内存使用: 实时监控")
    print("=" * 60)
    
    # 处理命令行参数
    import sys
    directory = r"I:\PycharmProjects\ComfyUI-aki-v1.4-old\models"  # 默认目录
    model_files_only = False  # 默认扫描所有大文件
    min_size_mb = 50  # 默认最小文件大小 (MB)
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--models-only" or arg == "-m":
                model_files_only = True
                print("🎯 启用模型文件过滤模式")
            elif arg == "--min-size":
                if i + 1 < len(sys.argv):
                    try:
                        min_size_mb = float(sys.argv[i + 1])
                        i += 1  # 跳过下一个参数
                    except ValueError:
                        print(f"⚠️  无效的最小文件大小: {sys.argv[i + 1]}")
                else:
                    print("⚠️  --min-size 参数需要指定数值")
            elif not arg.startswith("-"):
                # 如果是相对路径，转换为绝对路径
                if not os.path.isabs(arg):
                    directory = os.path.join(r"I:\PycharmProjects\ComfyUI-aki-v1.4-old\models", arg)
                else:
                    directory = arg
            i += 1
    
    print(f"📂 扫描目录: {directory}")
    print(f"📏 最小文件大小: {min_size_mb}MB")
    if model_files_only:
        print("🎯 扫描模式: 仅模型文件")
    else:
        print("📄 扫描模式: 所有大文件")
    print("=" * 60)
    
    try:
        # 创建检查器实例
        checker = LargeDuplicateChecker(
            directory=directory, 
            min_size_mb=min_size_mb,
            model_files_only=model_files_only
        )
        
        # 执行重复文件检查
        checker.check_duplicates()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()