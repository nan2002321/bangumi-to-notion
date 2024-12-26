from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
from functions import load_config, save_config, perform_search, get_bangumi_info, notion_page_cheat
from notion_client import Client
from updatenotion import AnimeBGMUpdater  # 导入 AnimeBGMUpdater 类

class ConfigWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bangumi to Notion - 配置")
        self.root.geometry("400x200")
        
        # 尝试从 JSON 文件读取配置
        config = load_config()
        if config:
            # 如果配置存在，直接打开搜索窗口
            SearchWindow(config['notion_key'], config['database_id'])
            self.root.destroy()
            return
            
        # 如果配置不存在，显示配置窗口
        # Notion API Key
        self.notion_key_label = tk.Label(self.root, text="Notion API Key:")
        self.notion_key_label.pack(pady=5)
        self.notion_key_entry = tk.Entry(self.root, width=50)
        self.notion_key_entry.pack(pady=5)

        # Database ID
        self.database_id_label = tk.Label(self.root, text="Database ID:")
        self.database_id_label.pack(pady=5)
        self.database_id_entry = tk.Entry(self.root, width=50)
        self.database_id_entry.pack(pady=5)

        # Confirm Button
        self.confirm_button = tk.Button(self.root, text="确认", command=self.confirm)
        self.confirm_button.pack(pady=20)

        self.notion_key = None
        self.database_id = None

    def confirm(self):
        self.notion_key = self.notion_key_entry.get()
        self.database_id = self.database_id_entry.get()
        
        if not self.notion_key or not self.database_id:
            messagebox.showerror("错误", "请填写所有字段")
            return
            
        # 保存配置到 JSON 文件
        save_config(self.notion_key, self.database_id)
        
        self.root.destroy()
        SearchWindow(self.notion_key, self.database_id)

class SearchWindow:
    def __init__(self, notion_key, database_id):
        self.root = tk.Tk()
        self.root.title("Bangumi to Notion - 搜索")
        self.root.geometry("1000x800")
        
        self.notion_key = notion_key
        self.database_id = database_id
        self.search_results = []

        # Search Frame
        search_frame = tk.Frame(self.root)
        search_frame.pack(pady=10, padx=10, fill='x')

        self.keyword_entry = tk.Entry(search_frame, width=40)
        self.keyword_entry.pack(side='left', padx=5)
        self.keyword_entry.bind('<Return>', lambda event: self.search_bangumi())
        
        self.search_button = tk.Button(search_frame, text="搜索", command=self.search_bangumi)
        self.search_button.pack(side='left', padx=5)
        
        # 添加批量导入按钮
        self.batch_button = tk.Button(search_frame, text="批量导入", command=self.batch_import)
        self.batch_button.pack(side='left', padx=5)

        # 添加更新导演和制作公司按钮
        self.update_button = tk.Button(search_frame, text="更新导演和制作公司", command=self.update_director_and_production)
        self.update_button.pack(side='left', padx=5)

        # 添加刷新 anime.json 按钮
        self.refresh_button = tk.Button(search_frame, text="刷新 anime.json", command=self.load_anime_json)
        self.refresh_button.pack(side='left', padx=5)

        # 添加清空 JSON 文件按钮
        self.clear_button = tk.Button(search_frame, text="清空 JSON 文件", command=self.clear_json_files)
        self.clear_button.pack(side='left', padx=5)

        # Results Frame
        results_frame = tk.Frame(self.root)
        results_frame.pack(pady=10, padx=10, fill='both', expand=True)

        # Results List
        self.results_list = ttk.Treeview(results_frame, columns=('title', 'name_cn', 'id'), show='headings')
        self.results_list.heading('title', text='标题')
        self.results_list.heading('name_cn', text='中文名')
        self.results_list.heading('id', text='ID')
        self.results_list.pack(side='left', fill='both', expand=True)

        # Scrollbar for Results
        scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.results_list.yview)
        scrollbar.pack(side='right', fill='y')
        self.results_list.configure(yscrollcommand=scrollbar.set)

        # Add Button
        self.add_button = tk.Button(self.root, text="添加到 Notion", command=self.add_to_notion)
        self.add_button.pack(pady=10)

        # Status Label
        self.status_label = tk.Label(self.root, text="")
        self.status_label.pack(pady=10)

        # Anime.json List Frame
        anime_frame = tk.Frame(self.root)
        anime_frame.pack(pady=10, padx=10, fill='both', expand=True)

        # Anime.json List
        self.anime_list = ttk.Treeview(anime_frame, columns=('title', 'id'), show='headings')
        self.anime_list.heading('title', text='番剧名称')
        self.anime_list.heading('id', text='ID')
        self.anime_list.pack(side='left', fill='both', expand=True)

        # Scrollbar for Anime List
        anime_scrollbar = ttk.Scrollbar(anime_frame, orient='vertical', command=self.anime_list.yview)
        anime_scrollbar.pack(side='right', fill='y')
        self.anime_list.configure(yscrollcommand=anime_scrollbar.set)

        # 加载 anime.json 数据
        self.load_anime_json()

    def load_anime_json(self):
        """加载 anime.json 文件中的数据并显示在列表中"""
        try:
            # 清空当前列表内容
            for item in self.anime_list.get_children():
                self.anime_list.delete(item)
            
            if os.path.exists('anime.json'):
                with open('anime.json', 'r', encoding='utf-8') as f:
                    anime_data = json.load(f)
                    for item in anime_data:
                        self.anime_list.insert('', 'end', values=(item['title'], item['id']))
                    self.status_label.config(text="已刷新 anime.json")
            else:
                self.status_label.config(text="anime.json 文件不存在")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载 anime.json 文件失败: {e}")

    def search_bangumi(self):
        keyword = self.keyword_entry.get()
        if not keyword:
            messagebox.showerror("错误", "请输入搜索关键词")
            return

        # Clear previous results
        for item in self.results_list.get_children():
            self.results_list.delete(item)

        search_results = perform_search(keyword)
        if not search_results:
            self.status_label.config(text="未找到相关动画")
            return

        self.search_results = search_results
        for result in search_results:
            self.results_list.insert('', 'end', values=(
                result['name'],
                result['name_cn'],
                result['id']
            ))

    def add_to_notion(self):
        selection = self.results_list.selection()
        if not selection:
            messagebox.showerror("错误", "请选择一个条目")
            return

        item = self.results_list.item(selection[0])
        bangumi_id = str(item['values'][2])
        
        try:
            notion = Client(auth=self.notion_key)
            info = get_bangumi_info(bangumi_id)
            
            if info is not None:
                # 检查必要字段是否存在
                if not info['title']:
                    raise ValueError("无法获取标题信息")
                    
                # 处理日期格式
                if info['air_date']:
                    # 确保日期格式正确
                    try:
                        datetime.strptime(info['air_date'], '%Y-%m-%d')
                    except ValueError:
                        # 如果日期格式不正确，移除日期字段
                        info['air_date'] = None
                
                notion_page_cheat(info, bangumi_id, notion, self.database_id)
                self.status_label.config(text=f"成功添加：{info['title']}")
                messagebox.showinfo("成功", f"已成功添加《{info['title']}》到 Notion")
            else:
                self.status_label.config(text="获取动画信息失败")
                messagebox.showerror("错误", "获取动画信息失败")
        except Exception as e:
            error_msg = str(e)
            self.status_label.config(text=f"添加失败：{error_msg}")
            messagebox.showerror("错误", f"添加失败：{error_msg}")

    def batch_import(self):
        try:
            # 读取 anime.txt 文件
            if not os.path.exists('anime.txt'):
                messagebox.showerror("错误", "未找到 anime.txt 文件")
                return
                
            with open('anime.txt', 'r', encoding='utf-8', errors='ignore') as f:
                anime_list = [line.strip() for line in f if line.strip()]
            
            if not anime_list:
                messagebox.showerror("错误", "anime.txt 文件为空")
                return
            
            # 记录成功和失败的条目
            success_count = 0
            failed_items = []
            
            # 处理每个番剧
            for anime_name in anime_list:
                try:
                    # 搜索番剧
                    search_results = perform_search(anime_name)
                    if not search_results:
                        failed_items.append(f"{anime_name} - 未找到搜索结果")
                        continue
                    
                    # 查找完全匹配的结果
                    exact_match = None
                    for result in search_results:
                        if result['name'] == anime_name or result['name_cn'] == anime_name:
                            exact_match = result
                            break
                    
                    if not exact_match:
                        failed_items.append(f"{anime_name} - 未找到完全匹配的结���")
                        continue
                    
                    # 获取详细信息并添加到 Notion
                    bangumi_id = str(exact_match['id'])
                    info = get_bangumi_info(bangumi_id)
                    
                    if info is not None:
                        # 处理日期格式
                        if info['air_date']:
                            try:
                                datetime.strptime(info['air_date'], '%Y-%m-%d')
                            except ValueError:
                                info['air_date'] = None
                        
                        notion = Client(auth=self.notion_key)
                        notion_page_cheat(info, bangumi_id, notion, self.database_id)
                        success_count += 1
                        self.status_label.config(text=f"正在处理: {anime_name}")
                        self.root.update()
                    else:
                        failed_items.append(f"{anime_name} - 获取详细信息失败")
                
                except Exception as e:
                    failed_items.append(f"{anime_name} - 处理出错: {str(e)}")
            
            # 显示处理结果
            result_message = f"批量导入完成\n成功: {success_count} 个\n"
            if failed_items:
                result_message += f"失败: {len(failed_items)} 个\n\n失败列表:\n" + "\n".join(failed_items)
            
            self.status_label.config(text=f"批量导入完成，成功：{success_count}，失败：{len(failed_items)}")
            messagebox.showinfo("批量导入结果", result_message)
            
        except Exception as e:
            messagebox.showerror("错误", f"批量导入过程出错：{str(e)}")

    def update_director_and_production(self):
        """更新导演和制作公司信息"""
        try:
            # 创建 AnimeBGMUpdater 实例
            updater = AnimeBGMUpdater(self.notion_key, self.database_id)
            
            # 清空当前列表
            for item in self.anime_list.get_children():
                self.anime_list.delete(item)
            
            # 执行更新
            self.status_label.config(text="正在更新导演和制作公司信息...")
            self.root.update()
            
            updater.main('anime.json')
            
            # 更新完成后刷新列表
            self.load_anime_json()
            
            self.status_label.config(text="导演和制作公司信息更新完成")
            messagebox.showinfo("成功", "已完成导演和制作公司信息的更新")
            
        except Exception as e:
            error_msg = str(e)
            self.status_label.config(text=f"更新失败：{error_msg}")
            messagebox.showerror("错误", f"更新失败：{error_msg}")

    def clear_json_files(self):
        """清空所有 JSON 文件"""
        try:
            # 要清空的文件列表
            json_files = ['anime.json', 'anime_details_processed.json', 'anime_details.json']
            cleared_files = []
            
            for file_name in json_files:
                try:
                    if os.path.exists(file_name):
                        # 清空文件内容为空列表
                        with open(file_name, 'w', encoding='utf-8') as f:
                            json.dump([], f)
                        cleared_files.append(file_name)
                except Exception as e:
                    print(f"清空 {file_name} 失败: {e}")
            
            # 清空列表显示
            for item in self.anime_list.get_children():
                self.anime_list.delete(item)
            
            # 显示成功消息
            if cleared_files:
                success_msg = f"已清空文件：\n" + "\n".join(cleared_files)
                self.status_label.config(text="已清空所有 JSON 文件")
                messagebox.showinfo("成功", success_msg)
            else:
                self.status_label.config(text="没有找到需要清空的 JSON 文件")
                messagebox.showinfo("提示", "没有找到需要清空的 JSON 文件")
            
        except Exception as e:
            error_msg = str(e)
            self.status_label.config(text=f"清空文件失败：{error_msg}")
            messagebox.showerror("错误", f"清空文件失败：{error_msg}")

def main():
    config = ConfigWindow()
    config.root.mainloop()

if __name__ == "__main__":
    main()