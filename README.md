# git_repository_backup_script 概述

此脚本是用于自动备份 git 仓库到其他服务器

## 1. 配置文件 

### config.ini

```ini
[common]
log_config=./log.conf       # log 配置文件路径
backup_dir=./git_repositorys  # git clone 临时目录
server_config_file=./remote_servers.txt  # 同步的目标服务器列表
repo_config_file=./repositorys.txt  # 同步的源服务器列表
```

### remote_servers.txt 

目标服务器列表，需要自行填写，每行是 git remote add <alias_name> <remote_url> 所需要的两个参数。服务器地址建议用 ssh 方式，可以做到无需交互输入密码。

示例：
```
backup_one  git@github.com:account-one
backup_two  git@bitbucket.org:account-two
```

### repositorys.txt 

源服务器列表，需要自行填写，每行是一个待备份的 git 仓库地址。

示例：
```
git@github.com:yourname/repo1.git
git@github.com:yourname/repo2.git
git@github.com:yourname/repo3.git
```

## 2. 运行方式

```bash
python3 backup.py
```

## 3. 执行原理

参考资料： https://help.github.com/articles/duplicating-a-repository/

主要逻辑为：

1. 以镜像方式 clone 到本地： git clone --mirror <repo_url> <local_path>
2. 拉取最新代码： git fetch -p origin
3. 添加远程备份服务器： git remote add <remote_name> <remote_url>
4. 提交到备份服务器： git push --mirror <remote_name>

