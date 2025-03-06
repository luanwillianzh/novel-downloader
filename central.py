#!/data/data/com.termux/files/usr/bin/python3.12
import os
import re
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
import ebooklib
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from ebooklib import epub
from rich.progress import Progress
from rich.console import Console
from rich.prompt import Confirm
from pick import pick
import urllib.parse

console = Console()
class Novel:
    def __init__(self, novel_link):
        self.novel_link = novel_link
        self.session = requests.Session()
        self.name, self.desc, self.cover, self.chapters = self.get_novel_info()
        self.novel_id = re.sub(r'\W+', '-', self.name).lower()
        os.makedirs(self.novel_id, exist_ok=True)

    def get_novel_info(self):
        response = self.session.get(self.novel_link, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        name = soup.select_one("h1[itemprop=name]").text.strip()
        desc = soup.select_one(".entry-content p").text.strip()
        cover = soup.select_one("div.thumb img")["src"]
        chapters = [a["href"] for a in soup.select("div.bixbox.bxcl.epcheck a")][::-1][:-2]
        console.print("\n[bold]Novel: [/bold]{}\n[bold]Descrição: [/bold]{}\n[bold]Capítulos: [/bold]{}\n".format(name, desc, len(chapters)))
        return name, desc, cover, chapters

    def download_chapter(self, chapter_url, progress, task):
      chapter_id = chapter_url.split("/")[-2]
      file_path = os.path.join(self.novel_id, chapter_id + ".html")
      if not os.path.exists(file_path):
        deu_erro = 1
        while deu_erro == 1:
          try:
            response = self.session.get(chapter_url, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.select_one("h1.entry-title").text.strip()
            subtitle = soup.select_one("div.cat-series").text.strip()
            content = str(soup.select_one("div.epcontent.entry-content"))
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("<html><head><title>{} - {}</title></head><body><h1>{}</h1><h2>{}</h2>{}</body></html>".format(title, subtitle, title, subtitle, content))
            time.sleep(2.9)
            deu_erro = 0
          except Exception as e:
            progress.console.log("[red]Erro ao baixar {}: {}[/red]".format(chapter_url, e))
      progress.update(task,advance=1)
      return chapter_url

    def create_file(self):
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor, Progress() as progress:
            task = progress.add_task("Downloading chapters", total=len(self.chapters))
            futures = {executor.submit(self.download_chapter, url, progress, task): url for url in self.chapters}
            for future in as_completed(futures):
                future.result()
        self.create_epub()

    def create_epub(self):
        book = epub.EpubBook()
        book.set_title(self.name)
        book.set_language('pt-BR')
        book.add_author("LuanW04")

        # Baixar a capa
        cover_path = os.path.join(self.novel_id, "cover.jpg")
        cover_data = self.session.get(self.cover).content
        with open(cover_path, "wb") as f:
            f.write(cover_data)
        book.set_cover("cover.jpg", cover_data)

        # Adicionar página de introdução
        intro_content = """
        <html>
        <head><title>Introdução</title></head>
        <body>
        <h1>{}</h1>
        <p>{}</p>
        </body>
        </html>
        """.format(self.name, self.desc)
        intro_chapter = epub.EpubHtml(title="Introdução", file_name="intro.html", content=intro_content)
        book.add_item(intro_chapter)

        chapters_list = [intro_chapter]
        progress = Progress()
        task = progress.add_task("Criando arquivo", total=len(self.chapters))
        for chapter_url in self.chapters:
          try:
            chapter_id = chapter_url.split("/")[-2]
            file_path = os.path.join(self.novel_id, chapter_id + ".html")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            h = BeautifulSoup(content, 'html.parser').select_one("title").text.strip()
            chapter = epub.EpubHtml(title=h, file_name="{}.html".format(chapter_id), content=content)
            book.add_item(chapter)
            chapters_list.append(chapter)
            progress.update(task, advance=1)
          except Exception as e:
            progress.console.log("[red]Erro {}: {}[/red]".format(chapter_id, e))

        book.toc = chapters_list
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        style = "body { font-family: Times, serif; }"
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)

        book.spine = ['nav', 'cover'] + chapters_list
        epub.write_epub(self.novel_id + ".epub", book, {})
        console.print("Epub created: {}.epub".format(self.novel_id))

def search(text):
    url = "https://centralnovel.com/wp-admin/admin-ajax.php"
    headers = {"Accept": "*/*", "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3", "TE": "trailers", "Content-Type": "application/x-www-form-urlencoded"}
    query = urllib.parse.quote_plus(text)
    data = "action=ts_ac_do_search&ts_ac_query={}".format(query)
    resp = requests.post(url, headers=headers, data=data, verify=False).json()
    lista = resp['series'][0]['all']
    if lista == []:
      console.print("Nada encontrado")
      exit()
    escolha = pick([ a['post_title'] for a in lista ], "Escolha a novel", indicator="=>", default_index=0)
    url = lista[escolha[1]]['post_link']
    return(url)

if __name__ == "__main__":
    novel_link = search(input("Pesquisar: "))
    novel = Novel(novel_link)
    ask = Confirm.ask("Deseja baixar?")
    if ask == True:
        novel.create_file()
    else:
        console.print("Saindo...")
