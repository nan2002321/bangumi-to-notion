import requests
import re
import json
from bs4 import BeautifulSoup
import time
import random
from fake_useragent import UserAgent
from notion_client import Client

class AnimeBGMUpdater:
    def __init__(self, notion_key, database_id):
        self.SEARCH_URL = 'https://bgm.tv/subject_search/{keyword}?cat=2'
        self.BASE_URL = 'https://bgm.tv'
        self.NOTION_KEY = notion_key
        self.DATABASE_ID = database_id
        self.notion = Client(auth=self.NOTION_KEY)

    def read_anime_list(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                anime_data = json.load(f)
                return [item['title'] for item in anime_data]
        except Exception as e:
            print(f"读取 {file_path} 文件失败: {e}")
            return []

    def search_anime_url(self, keyword):
        try:
            time.sleep(random.uniform(1, 3))
            ua = UserAgent()
            headers = {'User-Agent': ua.random}
            
            # 对搜索关键词进行处理
            encoded_keyword = keyword.replace('/', ' ').strip()
            encoded_keyword = requests.utils.quote(encoded_keyword)
            
            response = requests.get(
                self.SEARCH_URL.format(keyword=encoded_keyword), 
                headers=headers
            )
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            first_result = soup.find('a', class_='l')
            if first_result:
                return self.BASE_URL + first_result['href']
            else:
                print(f"未找到番剧详情页面: {keyword}")
        except Exception as e:
            print(f"搜索番剧详情页面失败: {e}")
        return None

    def extract_info(self, text, pattern):
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().replace('\n', '').replace('\r', '')
        return '未知'

    def get_anime_details(self, url):
        try:
            time.sleep(random.uniform(1, 3))
            ua = UserAgent()
            headers = {'User-Agent': ua.random}
            response = requests.get(url, headers=headers)
            response.encoding = 'utf-8'
            response.raise_for_status()
            page_text = response.text

            title_pattern = r'<h1 class="nameSingle">\s*<a[^>]*>([^<]+)</a>'
            title = self.extract_info(page_text, title_pattern)

            anime_make_pattern = r'动画制作:([^\n]*)'
            production = self.extract_info(page_text, anime_make_pattern)

            # 修改导演匹配模式，使用更精确的HTML结构匹配
            director_pattern = r'导演:([^\n]*)'
            director = self.extract_info(page_text, director_pattern)

            # 如果没找到导演信息，尝试使用日文关键词
            if director == '未知':
                director_pattern_jp = r'監督:([^\n]*)'
                director = self.extract_info(page_text, director_pattern_jp)

            return {
                'title': title,
                'production': production,
                'director': director
            }
        except Exception as e:
            print(f"获取番剧详情失败: {e}")
        return None

    def extract_text_from_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text().strip()

    def process_data(self, data):
        for item in data:
            if 'production' in item:
                item['production'] = self.extract_text_from_html(item['production'])
            if 'director' in item:
                item['director'] = self.extract_text_from_html(item['director'])
        return data

    def update_notion_page(self, database_id, page_title, new_properties):
        try:
            response = self.notion.databases.query(
                database_id=database_id,
                filter={
                    "property": "名称",
                    "title": {
                        "equals": page_title
                    }
                }
            )

            if not response.get("results"):
                print(f"未找到标题为 '{page_title}' 的页面")
                return

            page_id = response["results"][0]["id"]
            self.notion.pages.update(
                page_id=page_id,
                properties=new_properties
            )
            print(f"成功更新页面：{page_title}")
        except Exception as e:
            print(f"更新页面失败：{e}")

    def main(self, anime_json_path):
        anime_list = self.read_anime_list(anime_json_path)
        results = []

        for anime_name in anime_list:
            print(f"正在处理: {anime_name}")
            anime_url = self.search_anime_url(anime_name)
            if anime_url:
                details = self.get_anime_details(anime_url)
                if details:
                    results.append(details)
                    print(f"成功获取: {details}")
                else:
                    print(f"未找到番剧详情: {anime_name}")
            else:
                print(f"未找到番剧详情页面: {anime_name}")

        processed_data = self.process_data(results)

        with open('anime_details_processed.json', 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
        print("数据已保存到 anime_details_processed.json 文件中")

        for anime in processed_data:
            title = anime.get("title")
            production = anime.get("production")
            director = anime.get("director")

            if not title or not production or not director:
                print(f"数据不完整，跳过：{anime}")
                continue

            new_properties = {
                "制作公司": {
                    "rich_text": [
                        {
                            "text": {
                                "content": production
                            }
                        }
                    ]
                },
                "导演": {
                    "rich_text": [
                        {
                            "text": {
                                "content": director
                            }
                        }
                    ]
                }
            }

            self.update_notion_page(self.DATABASE_ID, title, new_properties)

# 示例用法
if __name__ == '__main__':
    notion_key = ""
    database_id = ""
    updater = AnimeBGMUpdater(notion_key, database_id)
    updater.main('anime.json')