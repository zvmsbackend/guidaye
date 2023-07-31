from threading import Thread
from itertools import count
import webbrowser
import argparse
import os.path
import json
import re

from bs4.element import ResultSet
import requests
import jinja2
import bs4


def crawl_link(link: dict, i: int, result: list) -> None:
    text = link['title']
    print('开始爬取', text)
    content = requests.get('https://b.guidaye.com' +
                           link['pic']).content.decode()
    content = re.search(
        r'<div.+?id="nr1".+?>([\s\S]+?)</div>', content).group(1)
    content = re.sub(
        r'src="/(.+?)"', 'src="https://b.guidaye.com/\\1"', content)
    result[i] = (text, content)
    print('爬取', text, '完成')


def main(id: str, title: str, path: str | None, browser: bool) -> None:
    result = []
    for n in count():
        data = json.loads(requests.post(
            f'https://b.guidaye.com/e/extend/bookpage/pages.php?id={id}',
            {'pageNum': n}
        ).content.decode())
        if data['totalPage'] == n:
            break
        print('第', n + 1, '页')
        former_length = len(result)
        result.extend([None] * len(data['list']))
        threads = []
        for i, link in enumerate(data['list'], former_length):
            thread = Thread(target=crawl_link, args=(
                link,
                i,
                result
            ))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
    path = determine_path(title, path)
    write_file(title, result, path)
    if browser:
        webbrowser.open(path)


def determine_path(title: str, path: str | None) -> str:
    if path is None:
        path = input('文件路径: ')
        if not path:
            return title + '.html'
    if os.path.isdir(path):
        return f'{path}/{title}.html'
    if not path.endswith('.html'):
        path += '.html'
    return path


def write_file(title: str, result: list, path: str) -> None:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
    template = env.get_template('template.html')
    open(path, 'w', encoding='utf-8').write(template.render(
        title=title,
        result=result
    ))
    print('写入到', os.path.abspath(path), '.')
    return
    open(path, 'w', encoding='utf-8').write(
        """<html>
<head>
  <link rel="stylesheet" href="https://cdn.staticfile.org/twitter-bootstrap/5.1.1/css/bootstrap.min.css">
</head>
<body>
  <div class="container">
    <h1 class="text-primary" id="top">{}</h1>
    <div class="row">
      <div class="col-4">
        <label>改变字体</label>
      </div>
      <div class="col">
        <input type="range" class="form-range" id="size" min="10" max="50">
      </div>
    </div>
    <div class="row">
      <div class="col-3">
        <nav class="navbar navbar-light bg-light flex-column align-items-stretch p-3">
        {}
        </nav>
      </div>
      <div class="col" id="content">
      {}
      </div>
    </div>
    <div class="fixed-bottom">
      <a href="#top">回到顶部</a><br>
      <a href="http://172.31.2.4:19198">回到主站</a>
    </div>
  </div>
  <script>
    const size = document.getElementById('size');
    const content = document.getElementById('content');
    size.addEventListener('change', (e) => {{
      content.style = 'font-size: ' + Math.floor(size.value);
    }});
  </script>
</body>
</html>""".format(
            title,
            '\n'.join(
                '<nav class="nav nav-pills flex-column"><a class="nav-link" href="#_{}">{}</a></nav>'.format(
                    i, text
                )
                for i, (text, _) in enumerate(result)
            ),
            '\n'.join(
                '<h4 id="_{}">{}</h4>\n{}'.format(
                    i, text, content
                )
                for i, (text, content) in enumerate(result)
            )
        )
    )


def search(title: str) -> ResultSet:
    soup = bs4.BeautifulSoup(requests.post('https://b.guidaye.com/e/search/index.php', {
        'keyboard': title,
        'show': 'title',
        'tempid': 1
    }).content.decode(), 'lxml')
    return soup.find('ul', class_='search-novel-list').find_all('a')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('title', help='书籍的标题')
    parser.add_argument('path', help='输出路径', nargs='?')
    parser.add_argument('-b', '--browser',
                        action='store_true', help='结束后打开浏览器')
    args = parser.parse_args()
    options = search(args.title)
    if not options:
        print('未找到')
    else:
        prompt = '选择书籍:\n{}\n'.format(
            '\n'.join(
                f'{i} {book.get_text()} {book["href"]}'
                for i, book in enumerate(options)
            )
        )
        selection = options[int(input(prompt))]
        id = re.match(r'.+/(\d+)/?$', selection['href']).group(1)
        main(id, selection.get_text(), args.path, args.browser)
