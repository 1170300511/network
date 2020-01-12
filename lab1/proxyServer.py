import socket
import threading
import os
import urllib.parse as urlp
import requests
import time
import json


class ProxyServer:

    def __init__(self):
        self.serverPort = 12138
        self.serverMainSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.serverMainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverMainSocket.bind(('127.0.0.1', self.serverPort))
        self.serverMainSocket.listen(10)
        self.HTTP_BUFFER_SIZE = 8192
        self.__cache_dir = './cache/'
        self.__make_cache()

    def __make_cache(self):
        if not os.path.exists(self.__cache_dir):
            os.mkdir(self.__cache_dir)

    @staticmethod
    def filter_web(url):
        with open('./filter.json', 'r') as f:
            filter_json = json.load(f)
            host_denied = filter_json['host']
            for url_denied in host_denied:
                if str(url) in url_denied:
                    return True
            return False

    @staticmethod
    def filter_fishing(url):
        with open('./filter.json', 'r') as f:
            filter_json = json.load(f)
            fishing = filter_json['fishing']
            for fish in fishing:
                if str(url) in fish:
                    return True
        return False

    @staticmethod
    def filter_ip(ip):
        """ 用于禁用制定IP """

        with open('./filter.json', 'r') as f:
            filter_json = json.load(f)
            ip_denied = filter_json['ip']
            if str(ip) in ip_denied:
                return True
            return False

    def tcp_get_connect(self, new_sock, address):
        message = new_sock.recv(self.HTTP_BUFFER_SIZE).decode("utf-8", 'ignore')
        print(message)
        megs = message.split("\n")  # 按照"\r\n"将请求消息的首部拆分为列表
        request_line = megs[0].strip().split()  # 请求消息第一行为Request Line
        # 将Request Line的method、URL和version 3个部分拆开
        if len(request_line) < 1:
            print("请求行中不包含URL")
            print(message)
            print(request_line)
            return
        else:
            url = urlp.urlparse(request_line[1])
        if self.filter_web(url.netloc):
            print("Denied ", url.geturl())
            with open('./404.html') as f:
                new_sock.sendall(f.read().encode("utf-8", 'ignore'))
            new_sock.close()
            return
        if self.filter_ip(address):  # 如果需要过滤某个IP
            with open('./403.html') as f:
                print("Illegal IP:" + url.geturl())
                new_sock.sendall(f.read().encode("utf-8", 'ignore'))
            new_sock.close()
            return
        if self.filter_fishing(url.netloc):
            # url = urlp.urlparse("http://www.cs.hit.edu.com")
            message = message.replace(url.netloc, "cs.hit.edu.cn")
            message = message.replace("http://math.hit.edu.cn", "http://cs.hit.edu.cn")
            url = urlp.urlparse(message.split('\r\n')[0].split()[1])
            # return requests.get("http://cs.hit.edu.cn").content
        new_out_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_name = self.__cache_dir + (url.netloc + url.path).replace('/', '_')
        flag_modified = False
        flag_exists = os.path.exists(file_name)
        if flag_exists:
            # 检查是否有缓存文件
            # 检查是否过期
            file_time = os.stat(file_name).st_mtime
            headers = {'If-Modified-Since': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(file_time))}
            send = requests.Session()
            send.headers.update(headers)
            response = send.get(url.geturl())
            if response.status_code == 304:
                print("Read from cache: " + file_name)
                with open(file_name, "r") as f:
                    new_sock.sendall(f.read().encode("utf-8", 'ignore'))
            else:
                os.remove(file_name)
                flag_modified = True
        if not flag_exists or flag_modified:
            out_host = url.netloc  # 使用urllib获取url中的host
            print("尝试连接:", url.geturl())
            # 利用新的向外连接的socket对目标主机进行访问
            new_out_socket.connect((out_host, 80))
            new_out_socket.sendall(message.encode("utf-8", 'ignore'))
            temp_file = open(file_name, "w")
            while True:
                buff = new_out_socket.recv(self.HTTP_BUFFER_SIZE)
                # buff = out_host(self.HTTP_BUFFER_SIZE)
                if not buff:
                    temp_file.close()
                    new_out_socket.close()
                    break
                temp_file.write(buff.decode("utf-8", 'ignore'))
                new_sock.sendall(buff)
            new_sock.close()

def main():
    proxy = ProxyServer()
    while True:
        print("Proxy server is ready to receive message:")
        new_sock, address = proxy.serverMainSocket.accept()
        # print(new_sock)
        threading.Thread(target=proxy.tcp_get_connect, args=(new_sock, address[0])).start()


if __name__ == '__main__':
    main()
