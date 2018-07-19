# -*- coding: utf8 -*-

# Author: liujun
# Date: 2018-07-18

# 备份 git 仓库。
# 参考资料： https://help.github.com/articles/duplicating-a-repository/
#
# 调用过程：
# 首次备份
# 1) git clone --mirror <repo>    以镜像裸库的方式 clone 一个仓库。
# 2) git remote add <backup_name> <backup_repo_url>    添加一个远程备份服务器。 (backup_name 不能用 origin， 不要覆盖原服务器地址)
# 3) git push --mirror <backup_name>    提交到备份服务器中。
#
# 已 clone 到本地的仓库
# 1) git fetch -p origin       从原服务器中拉取更新。(注意加 -p 选项，可以删除不再存在的分支)
# 2) git push --mirror <backup_name>    提交到备份服务器中。
#

import configparser
import logging.config
import os
import subprocess

import yaml

# 当前文件所在路径
# cur_dir = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
cur_dir = os.path.dirname(os.path.realpath(__file__))

# 加载配置文件
config = configparser.ConfigParser()
config.read(os.path.join(cur_dir, "config.ini"))

# 加载日志配置文件
log_config = config.get("common", "log_config", fallback="./log.conf")
log_config = os.path.realpath(os.path.join(cur_dir, os.path.expanduser(log_config)))
logging.config.dictConfig(yaml.load(open(log_config)))
logger = logging.getLogger()

class RemoteServer(object):
    """
    远程备份服务器类，包含两个属性：
    name:  添加到 git remote 中的名字
    remote_url:  添加到 git remote 中的url前缀

    相关调用： git remote add <name> <full_remote_url>
    """
    def __init__(self, name, remote_url):
        self.name = name
        self.remote_url = remote_url

    def get_name(self):
        return self.name

    def get_remote_url(self):
        return self.remote_url

    def __repr__(self):
        return 'RemoteServer({0.name!r}, {0.remote_url!r})'.format(self)

    def __str__(self):
        return 'RemoteServer {{name:"{0.name!s}", remote_url:"{0.remote_url!s}"}}'.format(self)


class GitRepository(object):
    """
    需要备份的仓库类，包含两个属性：
    repository_name: 仓库名称
    url:  原服务器地址
    """
    def __init__(self, url):
        names = url.split("/")
        self.repository_name = names[len(names)-1]
        self.url = url

    def get_repository_name(self):
        return self.repository_name

    def get_url(self):
        return self.url

    def __repr__(self):
        return 'GitRepository({0.url!r})'.format(self)

    def __str__(self):
        return 'GitRepository {{name:"{0.repository_name!s}", url:"{0.url!s}"}}'.format(self)


class GitBackupManager(object):
    """
    负责备份 git 仓库。主要逻辑为：
    1) 以镜像方式 clone 到本地： git clone --mirror <repo_url> <local_path>
    2) 拉取最新代码： git fetch -p origin
    3) 添加远程备份服务器： git remote add <remote_name> <remote_url>
    4) 提交到备份服务器： git push --mirror <remote_name>
    """

    def __init__(self, backup_dir):
        self.backup_dir = backup_dir
        self.repositorys = []
        self.remote_servers = []

    def add_repositorys(self, repositorys):
        if not isinstance(repositorys, list):
            raise ValueError("repositorys must be a list")
        for repo in repositorys:
            if not isinstance(repo, GitRepository):
                continue
            logger.info("add new repository: %s", repo)
            self.repositorys.append(repo)

    def add_remote_servers(self, servers):
        if not isinstance(servers, list):
            raise ValueError("servers must be a list")
        for server in servers:
            if not isinstance(server, RemoteServer):
                continue
            logger.info("add new server: %s", server)
            self.remote_servers.append(server)

    def backup(self):
        logger.info("准备备份。 共 %d 个仓库。", len(self.repositorys))

        cur_index = 0
        for repo in self.repositorys:
            cur_index += 1
            repo_name = repo.get_repository_name()
            logger.info("准备备份第 %d 个仓库 [%s]。", cur_index, repo_name)

            try:
                dest_path = os.path.join(self.backup_dir, repo_name)
                if not os.path.exists(dest_path):
                    # 未进行 clone, 先 clone, 添加服务器，并上传。
                    logger.info("[%s]: 正在拉取仓库代码。", repo_name)
                    os.system("git clone --mirror {url} {dest_path}".format(url=repo.get_url(), dest_path=dest_path))

                remotes = subprocess.getoutput("cd {path} && git remote".format(path=dest_path))
                remote_list = remotes.split()
                for server in self.remote_servers:

                    logger.info("[%s]: 更新仓库代码 。", repo_name)
                    os.system("cd {path} && git fetch -p origin".format(path=dest_path))

                    server_name = server.get_name()
                    if not server_name in remote_list:
                        logger.info("[%s]: 添加 remote [%s] 。", repo_name, server_name)
                        os.system("cd {path} && git remote add {server_name} {server_url}/{repo_name}".format(
                                    path=dest_path, server_name=server_name, server_url=server.get_remote_url(),
                                    repo_name=repo_name))
                    logger.info("[%s]: 提交代码至 remote [%s] 。", repo_name, server_name)
                    os.system("cd {path} && git push --mirror {server_name}".format(path=dest_path, server_name=server_name))

                logger.info("完成备份第 %d 个仓库 [%s]。", cur_index, repo_name)
            except Exception:
                logger.exception("备份第 %d 个仓库 [%s] 发生异常！", cur_index, repo_name)

        logger.info("完成备份所有仓库。")

def read_mirror_servers(file_name):
    result = []
    with open(file_name, "r") as fh:
        lines = fh.readlines()
        for line in lines:
            parts = line.split()
            assert(len(parts) == 2)
            server = RemoteServer(name=parts[0], remote_url=parts[1])
            result.append(server)
            logger.info("加载配置 server '%s' '%s'", parts[0], parts[1])
    return result

def read_backup_repositorys(file_name):
    result = []
    with open(file_name, "r") as fh:
        lines = fh.readlines()
        for line in lines:
            line = line.split()[0]
            repo = GitRepository(url=line)
            result.append(repo)
            logger.info("加载配置 repo '%s'", line)
    return result

def main():
    # 加载备份服务器列表
    server_config_file = config.get("common", "server_config_file", fallback="./remote_servers.txt")
    server_config_file = os.path.realpath(os.path.join(cur_dir, os.path.expanduser(server_config_file)))
    server_list = read_mirror_servers(server_config_file)

    # 加载仓库列表
    repo_config_file = config.get("common", "repo_config_file", fallback="./repositorys.txt")
    repo_config_file = os.path.realpath(os.path.join(cur_dir, os.path.expanduser(repo_config_file)))
    repo_list = read_backup_repositorys(repo_config_file)

    # 初始化 manager
    backup_dir = config.get("common", "backup_dir", fallback="./git_repositorys")
    backup_dir = os.path.realpath(os.path.join(cur_dir, os.path.expanduser(backup_dir)))
    manager = GitBackupManager(backup_dir=backup_dir)

    manager.add_remote_servers(server_list)
    manager.add_repositorys(repo_list)

    manager.backup()


if __name__ == "__main__":
    main()
