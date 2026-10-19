# Shell 脚本系统学习计划（长期 · 约 26 周）

> 目标读者：懂电脑基础（会用 Linux 命令、知道什么是进程/文件/权限），
> 但从未系统写过脚本的人。
> 最终目标：能独立编写**可维护、可调试、够健壮**的生产级脚本，
> 而不是"能在自己机器上跑一次"的脚本。

---

## 使用说明

- **每天 30–60 分钟**，周末留 2 小时做阶段项目。
- 每个阶段结构统一：目标 → 知识点 → 练习 → 项目 → 验收标准 → 常见坑。
- **练习必须手敲**，不要复制粘贴。抄会了 ≠ 会写。
- 每写完一个脚本，先跑 `shellcheck 脚本名`，把它当作"编译器警告"看待。
- 准备一个 `notes.md`，记录每次卡住超过 10 分钟的坑——那才是你真正的知识。

### 关于学习顺序（重要）

本计划刻意遵循一条原则：**先建立起"命令怎么跑起来"的地基，再往里填技巧。**
很多人学 Shell 卡住，不是因为不聪明，而是因为教程在前面引用了后面才该讲的东西
（比如还没讲清楚 `${}` 是什么，就直接用了 `${s#pattern}`）。
所以阶段 1 的顺序被重新组织为：

> 变量基础 → 引号 → 特殊参数 → 参数扩展 → 算术 → 条件 → 循环 → 函数

每一节只依赖它前面已经讲过的内容。看到看不懂的东西，先回头确认前面那一节读懂了。

---

## 📌 计划总览 + 进度看板

> 做完一格就把 `[ ]` 改成 `[x]` 打钩。每阶段的**详细任务框**在对应章节里。

| 阶段 | 周次 | 主题 | 产出 |
|------|------|------|------|
| 0 | 第1周 | 心智模型：文本流、文件描述符 0/1/2 | 能解释 `echo *` 为什么打印文件名 |
| 1 | 2–5周 | 语法地基：变量引用、条件、循环、函数 | 猜数字、参数校验脚本等 5 个小工具 |
| 2 | 6–10周 | 三剑客：grep/sed/awk + sort/uniq/cut | `logstats.sh` 日志分析器 |
| 3 | 11–12周 | 正则：BRE/ERE/PCRE、与通配符的区别 | 能校验手机号、提取邮箱、改写日期 |
| 4 | 13–16周 | 工程化：`set -euo pipefail`、trap、getopts、shellcheck | 每个脚本升级成带 `-h` 和错误处理的版本 |
| 5 | 17–20周 | 进程并发：后台任务、wait -n、flock、cron | `healthcheck.sh` 系统健康巡检 |
| 6 | 21–26周 | 综合实战 5 个项目 | 日志平台、备份轮转、自动部署（带回滚）、迷你进程管理器 |

### 阶段进度（7 个主框）
- [ ] **阶段 0**：心智模型（第 1 周）
- [ ] **阶段 1**：语法地基（第 2–5 周）
- [ ] **阶段 2**：文本处理三剑客（第 6–10 周）
- [ ] **阶段 3**：正则表达式（第 11–12 周）
- [ ] **阶段 4**：脚本工程化（第 13–16 周）
- [ ] **阶段 5**：进程、并发与系统交互（第 17–20 周）
- [ ] **阶段 6**：综合实战项目（第 21–26 周）

### 里程碑（毕业检查）
- [ ] 能独立写出带参数解析 + 错误处理 + 日志的脚本
- [ ] 能用一行管道在 5 分钟内分析陌生日志
- [ ] 完成至少 3 个阶段 6 的实战项目
- [ ] 所有脚本 `shellcheck` 零警告
- [ ] 有一个放了脚本的 GitHub 仓库

---

## 阶段 0：心智模型（第 1 周）

### 目标
建立三个核心心智模型，后面所有内容都建立在这之上。

### 知识点
1. **一切皆文本流**：命令的输入是文本，输出也是文本。管道就是把上一个的输出接到下一个的输入。
2. **一切皆文件**：终端是文件（`/dev/tty`），进程有 3 个标准文件描述符：
   - `0` stdin（标准输入）
   - `1` stdout（标准输出）
   - `2` stderr（标准错误）
3. **Shell 是解释器 + 语言**：它先做"展开"（变量、通配符、命令替换），再把结果交给真正的命令执行。
   这个顺序是几乎所有"诡异现象"的根源。

### 练习
- [ ] 观察三种流：
```bash
ls /nonexist                  # stdout 和 stderr 混在一起，看不出来
ls /nonexist 2>/dev/null      # 错误被丢弃
ls /nonexist 1>/dev/null      # 正常输出被丢弃，只剩错误
```
- [ ] 管道串联：
```bash
cat /etc/passwd | head -5 | cut -d: -f1
```

### 验收
- [ ] 能向别人解释：`echo *` 为什么打印的不是 `*`？

### 常见坑
- 分不清 stdout 和 stderr，导致日志里全是报错或全是空白。

---

## 阶段 1：语法地基（第 2–5 周）

### 目标
掌握变量、引号、条件、循环、函数——写出 50 行以内的逻辑脚本。

### 知识点

#### 1.1 变量基础（**最重要的一节，先看这里**）

Shell 里定义一个变量就是 `名字=值`。**`=` 两边不能有空格。**

```bash
name="Tang"        # 定义变量（注意：不能写成 name = "Tang"）
echo $name         # 取值 → Tang
echo ${name}       # 取值（加花括号）→ Tang
echo "你好 $name"  # → 你好 Tang
unset name         # 删除变量
```

**三种取值写法的区别：**

```bash
name="Tang"

echo $name-world       # Tang-world   （这里刚好对）
echo "$name123"        # （空）        ❌ 它以为变量名叫 name123！

echo "${name}123"      # Tang123      ✅ 花括号划清变量名边界
echo "${name}"         # Tang         ✅ 加引号最安全（防空格/通配符）
```

结论：
- 裸写 `$name` 能用，但紧挨字母/数字时会认错变量名。
- **`${name}`** 用花括号明确边界，**而且只有花括号才能接操作符**（见 1.4 参数扩展）。这就是为什么后面一堆 `${...}` 的写法必须带花括号。
- **`"$name"`** 加双引号，防止值里的空格被拆开（见 1.2）。

**变量的种类：**

```bash
local_var="普通变量"
export ENV_VAR="环境变量"     # 子进程也能读到
readonly PI=3.14              # 只读，不能再改
```

记住：**Bash 的变量本质都是字符串**，没有类型，做数字运算要靠算术展开（见 1.5）。

#### 1.2 引号规则（最容易踩坑）

```bash
a="world"
echo 'hello $a'      # hello $a     单引号：原样输出，不解析
echo "hello $a"      # hello world  双引号：解析变量、命令
echo hello $a        # hello world  不加引号：也解析，但危险
```

- **单引号 `'...'`**：所见即所得，里面任何东西都不解析。想让 `$` 当普通字符就用它。
- **双引号 `"..."`**：允许 `$变量`、`$(命令)` 展开。
- **不加引号**：也展开，但值里的空格会被拆成多个参数、通配符 `*` 会展开成文件名——**大多数 bug 的来源**。

```bash
file="my doc.txt"
cp $file /tmp/       # ❌ 被拆成 my 和 doc.txt 两个参数
cp "$file" /tmp/     # ✅ 一个完整参数
```

**铁律：变量能加双引号就加双引号。**

转义：

```bash
echo "他说：\"你好\""    # 双引号里用 \ 转义双引号
echo 'it'\''s'           # 单引号里塞单引号的写法
echo $'line1\nline2'     # $'...' 支持 \n \t 等转义
```

#### 1.3 特殊参数（Shell 自动维护）

这些不是普通变量，是 shell 帮你填好的。

| 变量 | 含义 |
|------|------|
| `$0` | 脚本名 |
| `$#` | 位置参数个数 |
| `$1` `$2` … | 第 1、2 个参数（≥10 要写 `${10}`）|
| `$@` | 所有参数，**每个参数保持独立** |
| `$*` | 所有参数，被 `IFS` 拼成**一个字符串** |
| `$?` | 上一条命令的退出码（`0`=成功）|
| `$$` | 当前进程 PID |
| `$RANDOM` | 随机数 0–32767 |
| `$LINENO` | 当前行号 |

```bash
#!/usr/bin/env bash
if [ "$#" -lt 2 ]; then
  echo "用法: $0 <源> <目标>"
  exit 1
fi
echo "第1个参数: $1"
echo "第2个参数: $2"
echo "共 $# 个参数"
```

**`"$@"` vs `"$*"`（重点）：**

```bash
# 传给脚本：./s.sh "a b" c

for arg in "$@"; do echo "[$arg]"; done
# [a b]
# [c]          ← 两个独立参数，含空格的没被拆

for arg in "$*"; do echo "[$arg]"; done
# [a b c]      ← 合成一个字符串

# ❌ 危险：不加引号的 $@
for arg in $@; do echo "[$arg]"; done
# [a] [b] [c]  ← "a b" 被拆开了
```

**规则：循环所有参数，永远用 `"$@"`。**

退出码 `$?`：`0` = 成功，非 `0` = 失败。

```bash
if grep -q "error" app.log; then echo "找到了"; fi   # 直接判断更地道
```

`$$` / `$RANDOM` 实战：

```bash
tmp="/tmp/work.$$.$RANDOM"     # 每个进程唯一，避免冲突
n=$((RANDOM % 100 + 1))        # 1–100 随机整数
```

#### 1.4 参数扩展（进阶字符串操作）

先记住外壳：**`${变量名 操作符 模式}`**。
- `${ }` 是固定外壳（就是 1.1 里那个花括号）。
- 里面第一个词是**变量名**——教程里常写成 `s`，那只是 "string" 的随手起名，**换成 `name`、`path` 都行**。
- 后面接的操作符决定做什么。

下面用 `s="Hello-World"` 举例。**请先在心里把 `s` 翻译成"某个变量"。**

**（1）取长度 `${#s}`**

```bash
s="Hello-World"
echo "${#s}"        # 11
```

`#` 紧跟在变量名前面就是"取长度"，别和下面的裁剪 `#` 搞混。

**（2）替换 `${s/旧/新}`、`${s//旧/新}`**

```bash
echo "${s/World/Sh}"     # Hello-Sh        替换第一个匹配
echo "${s//l/L}"         # HeLLo-WorLd     双斜杠：替换全部
echo "${s/l/}"           # Helo-World      删掉（replace 留空）
```

**（3）裁剪前缀/后缀（记清这张表）**

| 写法 | 从哪删 | 删多少 |
|------|--------|--------|
| `${s#pattern}`  | 开头（前缀）| 最短 |
| `${s##pattern}` | 开头 | 最长 |
| `${s%pattern}`  | 结尾（后缀）| 最短 |
| `${s%%pattern}` | 结尾 | 最长 |

口诀：
- **`#` 在键盘左边 → 管开头；`%` 在键盘右边 → 管结尾。**
- **单符号 = 最短匹配；双符号 = 最长匹配。**
- 被删的是"模式 `pattern`"，`*` 是通配符（任意字符），剩下的才是结果。

用 `s="Hello-World"` 推导：

```bash
echo "${s#*-}"    # 删最短前缀(*-)：Hello- 被删 → World
echo "${s##*-}"   # 删最长前缀：还是 Hello-   → World（只有一个 -，结果同）
echo "${s%-*}"    # 删最短后缀(-*)：-World 被删 → Hello
echo "${s%%-*}"   # 删最长后缀：还是 -World   → Hello
```

> ⚠️ 旧笔记里把 `${s%%-*}` 注释成"从右删掉最长**前缀**"是错的。
> `%%` 删的是**后缀**（从右边），`#`/`##` 才是删前缀（从左边）。

只有**多个分隔符**时，`#` 与 `##`、`%` 与 `%%` 才有区别。用路径最直观：

```bash
p="/home/tang/work/test/file.txt"

echo "${p#*/}"     # home/tang/work/test/file.txt   删最短前缀(*/)
echo "${p##*/}"    # file.txt                       ← 常用：取文件名
echo "${p%/*}"     # /home/tang/work/test           ← 取目录
echo "${p%%/*}"    # （空）                         删最长后缀(/*)
```

取扩展名：

```bash
f="report.tar.gz"
echo "${f##*.}"    # gz          最后一段
echo "${f%.*}"     # report.tar  去掉最后一段
```

**（4）子串 `${s:起始:长度}`**

```bash
echo "${s:0:5}"    # Hello       从 0 开始取 5 个
echo "${s:6}"      # World       从 6 开始取到末尾
echo "${s: -5}"    # World       从末尾倒数（注意 : 后有个空格）
```

**（5）默认值（极常用）**

```bash
echo "${name:-默认}"      # name 未定义/为空 → 用"默认"，不改 name
echo "${name:=默认}"      # 同上，并且把"默认"赋给 name
echo "${name:+有值}"      # name 有值 → 返回"有值"，否则空
echo "${name:?必须提供}"  # name 为空 → 报错退出（用于必填校验）

port="${1:-8080}"         # 实战：没传第 1 个参数就用 8080
```

#### 1.5 算术

```bash
a=5; b=3
echo $((a + b))          # 8
echo $((a % b))          # 2     取余
echo $((10 / 3))         # 3     整除
((a++))                  # 命令式写法，a 变成 6（这里不写 $）
if (( a > b )); then echo "a bigger"; fi
```

小数要用 `bc` 或 `awk`：

```bash
echo "scale=2; 10/3" | bc      # 3.33
```

#### 1.6 条件判断

```bash
if [ "$#" -eq 0 ]; then
  echo "没有参数"
elif [ "$#" -gt 5 ]; then
  echo "参数太多"
else
  echo "参数正常"
fi
```

`[ ]` 其实就是 `test` 命令，所以**方括号内外都要有空格**。

```bash
# 数值比较（不能用 ==）
[ "$a" -eq "$b" ]   # 相等      -ne 不等
[ "$a" -gt "$b" ]   # 大于      -ge 大于等于  -lt 小于  -le 小于等于

# 字符串比较
[ "$a" = "$b" ]     # 相等      != 不等
[ -z "$a" ]         # 为空
[ -n "$a" ]         # 非空

# 文件判断
[ -e "$f" ]  # 存在    -f 普通文件  -d 目录  -r 可读  -w 可写  -x 可执行

# 逻辑组合
[ -f a ] && [ -d b ]    # 且
[ -f a ] || [ -d b ]    # 或
```

**推荐用 `[[ ... ]]`（Bash 扩展）**，更安全、支持正则和通配符，`&&`/`||` 可直接写在里面：

```bash
[[ "$s" == Hello* ]]        # 通配符匹配
[[ "$s" =~ ^[0-9]+$ ]]      # 正则匹配
[[ -f file && -d dir ]]     # 无需转义的 &&
```

#### 1.7 循环

```bash
# for 遍历列表 / 文件
for f in *.txt; do echo "$f"; done
for f in "$@"; do echo "处理 $f"; done

# for 遍历数字
for i in {1..5}; do echo "$i"; done
for i in $(seq 1 5); do echo "$i"; done   # 大范围用 seq 更省内存

# while 读文件（正确姿势：不丢失含空格的行）
while IFS= read -r line; do
  echo "got: $line"
done < file.txt

# while 计数
n=0
while [ "$n" -lt 10 ]; do ((n++)); done

# case 分支
case "$1" in
  start)        echo "starting" ;;
  stop|restart) echo "stopping/restarting" ;;
  *)            echo "usage: $0 {start|stop}" ; exit 1 ;;
esac
```

控制：`break`（跳出整个循环）、`continue`（跳过本次）。

#### 1.8 函数

```bash
greet() {
  local name="$1"          # local 限定作用域，必须加
  echo "Hi, $name"
  return 0                 # 返回退出码（0–255），不是返回值
}

greet "Alice"

# 要"返回字符串"用 echo + 命令替换
get_os() { echo "linux"; }
os=$(get_os)
```

- 函数里 `$1 $2 $@ $#` 表示**函数的**参数，和脚本参数独立。
- 用 `local` 声明局部变量，避免污染全局。

### 练习（每个都要写出来）
- [ ] 写 `is_root.sh`：判断当前用户是否 root（`[ "$(id -u)" -eq 0 ]`），不是则退出码 1。
- [ ] 写 `backup.sh`：接收一个文件参数，不存在则报错退出；存在则复制为 `file.bak`。
- [ ] 写 `countdown.sh`：从 10 倒数到 1，最后打印 `Liftoff!`。
- [ ] 写 `guess.sh`：随机一个 1–100 的数，循环让用户猜，提示大了/小了，猜中退出。
- [ ] 写 `even_odd.sh`：遍历 1–20，用 `case` 或算术判断奇偶分行打印。
- [ ] 写 `strlab.sh`：给定 `s="Hello-World"`，用参数扩展分别打印它的长度、
  `-` 之后的部分、`-` 之前的部分、扩展名式替换结果。

### 验收
- [ ] 能不查资料写出"参数校验 + 循环 + 条件 + 函数"的 40 行脚本。
- [ ] 能解释 `$@` 和 `$*` 的区别，以及为什么循环参数要用 `"$@"`。
- [ ] 能说清 `${s#*-}` 里的 `s` 是什么，为什么必须用 `${ }` 而不能写 `$s#*-`。

### 常见坑
- 赋值时 `=` 两边加了空格，报"命令未找到"。
- 变量忘加引号：`rm $files` 在有空格文件名时会删错文件。
- `[ "$a" = "$b" ]` 里变量忘加引号，值为空时直接语法报错。
- 以为 `$s#*-` 能裁剪——不行，**操作符必须写在 `${ }` 里面**。
- 函数里忘写 `local`，污染全局变量。
- 用 `==` 在 POSIX `sh`（`dash`）下不兼容。

---

## 阶段 2：文本处理三剑客（第 6–10 周）

### 目标
Shell 的灵魂是文本处理。这一阶段要能像呼吸一样使用 `grep` / `sed` / `awk` / `sort` / `uniq`。

### 知识点

#### 2.0 命令替换与重定向全家桶

```bash
now=$(date +%F)              # 命令替换：把输出当值（推荐 $( )，别用反引号）

cmd > out.txt        # 覆盖写 stdout
cmd >> out.txt       # 追加写
cmd 2> err.txt       # 只重定向 stderr
cmd > out.txt 2>&1   # stdout 和 stderr 都进 out.txt（经典写法）
cmd &> all.txt       # 上面的简写（Bash）
cmd 2>/dev/null      # 丢弃错误

cat <<EOF            # Here-document：多行输入
line1
line2
EOF

grep "pattern" <<< "some text"   # Here-string：把字符串当输入
```

#### 2.1 grep（搜索）
```bash
grep "error" app.log                  # 基础搜索
grep -i "error" app.log               # 忽略大小写
grep -n "error" app.log               # 带行号
grep -v "error" app.log               # 反向：不含 error 的行
grep -c "error" app.log               # 统计行数
grep -E "err|warn" app.log            # 扩展正则（或）
grep -r "TODO" .                      # 递归目录
grep -A3 -B2 "error" app.log          # 显示前后几行（上下文）
grep --color=auto "error" app.log     # 高亮
```

#### 2.2 sed（流编辑器，改文本）
```bash
sed 's/old/new/' file.txt             # 每行第一个匹配替换
sed 's/old/new/g' file.txt            # 每行所有匹配替换
sed -i 's/old/new/g' file.txt         # 直接改文件（-i 建议先备份：-i.bak）
sed -n '5p' file.txt                  # 只打印第 5 行（-n 关闭自动打印）
sed -n '10,20p' file.txt              # 打印 10–20 行
sed '/pattern/d' file.txt             # 删除含 pattern 的行
sed '3i\new line' file.txt            # 在第 3 行前插入
sed '3a\new line' file.txt            # 在第 3 行后追加
```

#### 2.3 awk（结构化处理，最强大）
```bash
awk '{print $1}' file.txt             # 打印第 1 列（默认按空白分列）
awk -F: '{print $1, $3}' /etc/passwd  # 指定分隔符
awk '{print NR": "$0}' file.txt       # NR=行号，$0=整行
awk 'NR==5' file.txt                  # 打印第 5 行
awk '$3 > 100' file.txt               # 条件过滤

# 汇总统计（经典场景）
awk '{sum+=$2} END {print "total:", sum}' data.txt
awk '{count[$1]++} END {for (k in count) print k, count[k]}' log.txt

# BEGIN/END 在处理前后执行一次
awk 'BEGIN{print "start"} {print} END{print "end"}' file.txt
```

#### 2.4 排序、去重、统计
```bash
sort file.txt              # 排序
sort -n file.txt           # 按数字排序
sort -r file.txt           # 逆序
sort -u file.txt           # 排序 + 去重
uniq file.txt              # 去重（必须先 sort）
uniq -c file.txt           # 去重并计数
sort file.txt | uniq -c | sort -rn   # 词频统计（高频在前）
wc -l file.txt             # 行数（-w 词数，-c 字节数）
cut -d: -f1 /etc/passwd    # 按分隔符切列
tr -d '\r'                 # 删除字符
paste -sd, file.txt        # 用逗号把多行合并成一行
tee out.txt                # 既打印又写文件：cmd | tee out.txt
```

#### 2.5 xargs（把输出变成参数）
```bash
find . -name "*.tmp" | xargs rm                # 危险！文件名有空格会炸
find . -name "*.tmp" -print0 | xargs -0 rm     # 正确姿势
ls *.jpg | xargs -I{} cp {} /backup/           # {} 代替每个参数
cat urls.txt | xargs -P4 -I{} curl {}          # -P4 并发 4 个
```

### 练习
准备一份真实日志（可用 `apt install` 日志、nginx 日志，或自己造）。

- [ ] 统计日志里每个 IP 出现次数，取前 10：
   ```bash
   grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' access.log \
     | sort | uniq -c | sort -rn | head -10
   ```
- [ ] 用 `awk` 计算日志里所有请求的平均响应时间。
- [ ] 用 `sed` 把一个配置文件里所有 `old_host` 批量替换成 `new_host`（先 `.bak` 备份）。
- [ ] 用 `grep -c` 统计 ERROR 和 WARN 各多少条。
- [ ] 把 `dmesg` 输出里所有大写单词提取出来去重排序。

### 项目：`logstats.sh`
输入一个日志文件路径，输出：
- [ ] 总行数
- [ ] ERROR / WARN / INFO 各自数量和占比
- [ ] 出现最多的 5 个 IP
- [ ] 时间范围（最早和最晚的时间戳）
- [ ] 结果同时打印到屏幕和写入 `report.txt`

### 验收
- [ ] 给你一段陌生日志，能在 5 分钟内用一行管道回答"哪个字段最多/平均值是多少"。
- [ ] 能解释 `awk '{sum+=$2} END{print sum}'` 里 `END` 的作用。

### 常见坑
- `sed -i` 忘了先备份，改坏配置文件无法回滚。
- `xargs` 处理含空格/换行的文件名必须用 `-print0` / `-0`。
- `uniq` 前面忘了 `sort`，导致去重不干净。
- 中文/UTF-8 日志用 `awk` 按字节统计长度会错（`awk` 的 `$1` 按字节切）。

---

## 阶段 3：正则表达式（第 11–12 周）

### 目标
能读懂并写出常用正则，理解 BRE / ERE / PCRE 的区别。

### 知识点
```bash
# 三类正则
grep  "pattern"     # BRE（基本正则）：+ ? | ( ) 需要转义
grep -E "pattern"   # ERE（扩展正则）：+ ? | ( ) 直接用
grep -P "pattern"   # PCRE（Perl 正则）：\d \w \s 零宽断言等

# 常用元字符
.       任意单个字符
*       0 个或多个
+       1 个或多个（ERE）
?       0 个或 1 个（ERE）
^ $     行首 行尾
[]      字符集 [aeiou]
[^]     取反 [^0-9]
{}      重复次数 [0-9]{3}
|       或（ERE）
()      分组（ERE）
\b      单词边界（PCRE）

# 实例
grep -E '^[A-Z][a-z]+$' names.txt                  # 首字母大写的单词
grep -E '\b[0-9]{1,3}(\.[0-9]{1,3}){3}\b'          # IPv4 地址
grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+'        # 提取邮箱
echo "2026-10-12" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'   # 校验日期格式
```

### 正则 vs 通配符（**务必分清**）
| 场景 | 语法 | `*` 含义 | 例子 |
|------|------|---------|------|
| 文件名展开 | glob | 任意字符任意次 | `ls *.txt` |
| 模式匹配 | `[[ ]]` | 同 glob | `[[ $f == *.txt ]]` |
| 正则匹配 | `=~` / grep | 前面字符重复 | `[[ $f =~ \.txt$ ]]` |

### 练习
- [ ] 校验输入是否为合法的 11 位手机号。
- [ ] 从一段 HTML 里提取所有 `<a href="...">` 的链接。
- [ ] 把文本里所有的日期 `YYYY-MM-DD` 改成 `DD/MM/YYYY`（用 `sed -E`）。
- [ ] 匹配所有连续重复的单词（`grep -E '\b(\w+) \1\b'`，注意 PCRE）。

### 验收
- [ ] 能看懂这条正则并解释每一段：
```bash
grep -E '^([a-z0-9._%-]+)@([a-z0-9.-]+)\.([a-z]{2,})$' emails.txt
```

---

## 阶段 4：脚本工程化（第 13–16 周）

### 目标
从"能跑"进化到"能在生产用"：健壮、可维护、可配置、有帮助信息。

### 知识点

#### 4.1 脚本骨架（**每次写脚本都套这个模板**）
```bash
#!/usr/bin/env bash
# 作者 / 日期 / 用途
set -euo pipefail
# set -e   出错立即退出
# set -u   用未定义变量报错
# set -o pipefail  管道中任一失败则整体失败

# ---------- 配置 ----------
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_FILE="/var/log/${SCRIPT_NAME%.sh}.log"

# ---------- 工具函数 ----------
log()  { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
用法: $SCRIPT_NAME [选项] <参数>
  -v    详细输出
  -h    显示帮助
EOF
  exit "${1:-0}"
}

# ---------- 参数解析 ----------
verbose=0
while getopts ':vh' opt; do
  case "$opt" in
    v) verbose=1 ;;
    h) usage 0 ;;
    \?) die "未知选项: -$OPTARG" ;;
    :)  die "选项 -$OPTARG 需要参数" ;;
  esac
done
shift $((OPTIND - 1))
[[ $# -ge 1 ]] || usage 1

# ---------- 主逻辑 ----------
main() {
  local target="$1"
  [[ -e "$target" ]] || die "目标不存在: $target"
  log "处理 $target (verbose=$verbose)"
}

main "$@"
```

#### 4.2 退出码约定
```bash
0   成功
1   通用错误
2   误用（如参数错误）
126 不可执行
127 命令未找到
130 Ctrl-C (128+2)
```
让脚本既能被手动运行，也能被其他脚本调用（通过 `$?` 判断成败）。

#### 4.3 临时文件与安全
```bash
tmp="$(mktemp)"               # 让系统生成唯一且安全的临时文件
trap 'rm -f "$tmp"' EXIT      # 无论正常退出还是报错，都清理
workdir="$(mktemp -d)"        # 临时目录
trap 'rm -rf "$workdir"' EXIT
```

#### 4.4 信号与 trap
```bash
cleanup() { log "清理中..."; rm -f "$tmp"; }
trap cleanup EXIT             # 脚本退出时（任何原因）
trap 'echo "收到中断"; exit 130' INT
trap 'echo "收到终止"; exit 143' TERM
```

#### 4.5 颜色与格式化输出
```bash
RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
echo "${RED}失败${RESET}"
echo "${GREEN}成功${RESET}"
```

#### 4.6 调试技巧
```bash
bash -x script.sh arg1     # 执行时打印每条命令（追踪）
set -x                     # 在脚本内部开启；set +x 关闭
shellcheck script.sh       # 静态检查（装它！）
bashdb script.sh           # 断点调试器（进阶）
```

### 练习
- [ ] 把阶段 1 写的所有脚本补上：`set -euo pipefail`、`usage()`、参数校验、`log()`、`trap` 清理。
- [ ] 写 `sysinfo.sh`：收集系统信息（OS、内核、CPU、内存、磁盘），带 `--json` 选项输出 JSON。
- [ ] 写 `rename.sh`：批量重命名文件，支持 `--dry-run`（只打印不执行）和 `--suffix .bak`。
- [ ] 给每个脚本跑 `shellcheck`，把所有警告清零。

### 验收
- [ ] 别人拿到你的脚本，能通过 `-h` 看懂怎么用。
- [ ] 脚本中途被 `Ctrl-C` 或磁盘满报错时，临时文件能被清理。
- [ ] `shellcheck` 零警告。

### 常见坑
- 忘记 `shift $((OPTIND - 1))`，导致 `$1` 还是选项而不是参数。
- `set -e` 下某些写法会意外退出（如 `((x++))` 当 x=0 时返回非零）。
- `trap` 里用了未定义变量，导致清理失败。

---

## 阶段 5：进程、并发与系统交互（第 17–20 周）

### 目标
理解进程模型，能写后台任务、并发处理、与系统深度交互的脚本。

### 知识点

#### 5.1 后台与等待
```bash
long_task &
pid=$!
echo "后台 PID: $pid"
wait "$pid"            # 等它结束
echo "退出码: $?"

long_task > out.log 2>&1 &     # 后台任务输出重定向
```

#### 5.2 并发控制（重要）
```bash
max_jobs=5
for url in $(cat urls.txt); do
  curl "$url" &
  while (( $(jobs -rp | wc -l) >= max_jobs )); do
    wait -n     # 等任意一个结束（Bash 4.3+）
  done
done
wait
```

#### 5.3 进程查找与信号
```bash
pgrep -f "pattern"         # 按命令行找 PID
pkill -f "pattern"         # 按命令行杀
kill -0 "$pid"             # 探测进程是否存在（不真杀）
kill -TERM "$pid"          # 优雅终止（15）
kill -9 "$pid"             # 强制杀（9，尽量别用）
```

#### 5.4 文件锁（防止重复运行）
```bash
exec 200>/tmp/myscript.lock
if ! flock -n 200; then
  echo "已有实例在运行，退出"; exit 1
fi
# 后续代码持锁运行，脚本结束自动释放
```

#### 5.5 定时任务 cron
```bash
# crontab -e 添加（注意 cron 环境变量极少，用绝对路径）
*/5 * * * * /usr/local/bin/healthcheck.sh >> /var/log/hc.log 2>&1
```

#### 5.6 与系统深度交互
```bash
df -h | awk '$5+0 > 80 {print "磁盘告警:", $6, $5}'   # 磁盘 >80% 告警
free -m | awk '/Mem/{print "内存使用:", $3 "/" $2 "MB"}'
ss -tlnp | grep :80                                  # 端口监听
systemctl is-active nginx && echo "nginx 运行中"
```

### 项目：`healthcheck.sh`
- [ ] 检查：磁盘使用率、内存使用率、关键进程是否存活、关键端口是否监听。
- [ ] 任一异常则记录日志并发邮件/写入告警文件。
- [ ] 用 `flock` 防止重复运行。
- [ ] 配合 cron 每 5 分钟执行。

### 验收
- [ ] 能解释 `wait` 和 `wait -n` 的区别。
- [ ] 能写出"并发下载 100 个文件但最多同时 10 个"的脚本。
- [ ] 理解为什么 `kill -9` 是最后手段。

### 常见坑
- cron 里用了相对路径或依赖 `$PATH`，导致脚本在 cron 里失败。
- 后台任务的 stdout 没重定向，导致脚本莫名其妙挂住。
- 忘记 `wait`，脚本主流程先结束了，后台任务被杀。

---

## 阶段 6：综合实战项目（第 21–26 周）

### 目标
把前面所有内容融进真实场景，做出可以放进简历/工作里的东西。

### 项目清单（每个都要写 README + 用法示例 + shellcheck 清零）

- [ ] **1. 日志分析平台 `log-analyzer/`**
   - [ ] 解析多种格式日志（nginx / syslog / 自定义）
   - [ ] 生成统计报告（QPS、错误率、Top IP、响应时间分布）
   - [ ] 支持 `--since`/`--until` 时间过滤
   - [ ] 输出终端表格 + CSV + HTML

- [ ] **2. 自动备份与轮转 `backup/`**
   - [ ] 备份指定目录，增量（`rsync --link-dest`）
   - [ ] 按日期归档，保留最近 N 天
   - [ ] 可选压缩（`tar` + `gzip`/`zstd`）与加密（`gpg`）
   - [ ] 支持本地 + 远程（`ssh`/`rclone`）
   - [ ] 备份后校验（checksum），失败告警

- [ ] **3. 部署脚本 `deploy.sh`**
   - [ ] `deploy.sh <env> <version>`
   - [ ] 拉取代码 → 依赖安装 → 构建 → 停旧服务 → 起新服务 → 健康检查
   - [ ] 健康检查失败则**自动回滚**到上一版本
   - [ ] 全程彩色日志，可 `--dry-run`

- [ ] **4. 进程管理器 `mini-supervisor/`**（挑战）
   - [ ] 读配置文件，管理多个后台进程
   - [ ] 进程挂了自动重启（带退避）
   - [ ] `status` / `restart` / `stop` 子命令
   - [ ] 用 `flock` + PID 文件管理状态

- [ ] **5. dotfiles 管理器 `dotfiles.sh`**
   - [ ] 把 `~/.bashrc`、`~/.vimrc` 等软链到 git 仓库
   - [ ] `install` / `uninstall` / `update` 子命令
   - [ ] 支持新机器一键初始化

### 验收
- [ ] 每个项目：能被非作者（或一个月后的你）看懂并使用。
- [ ] 代码风格统一，`shellcheck` 清零，有错误处理和日志。
- [ ] 至少 3 个项目能演示"异常路径也处理了"。

---

## 持续提升（长期）

### 推荐资源（按优先级）
1. **《Linux 命令行与 Shell 脚本编程大全》**（Richard Blum）—— 系统全面，中文版好买。
2. **《Shell 脚本学习指南》**（Cameron Newham）—— 精炼，适合快速过。
3. **《sed & awk》**（Dougherty & Robbins）—— 三剑客圣经，配合 `sed/awk` 阶段看。
4. **《The Linux Command Line》**（William Shotts）—— 免费电子书，英文，讲得极清楚。
5. **ShellCheck 官网** https://www.shellcheck.net —— 每条警告都是一课。
6. **ExplainShell** https://explainshell.com —— 看不懂的命令粘进去逐段解释。
7. **Google Shell Style Guide** —— 生产脚本的代码规范标准。

### 保持手感的日常习惯
- [ ] 每天用 Shell 处理一件本来要手动做的事（哪怕只是重命名文件）。
- [ ] 每周读一个开源项目里的真实脚本（如 `/etc/init.d/`、Homebrew 的 formula、Docker 的 entrypoint）。
- [ ] 遇到重复劳动就问自己："这能不能写成脚本？"——能就写。
- [ ] 把自己写的脚本推到 GitHub，附 README。

### 进阶方向（学完 26 周后）
- **Bash 高级特性**：关联数组、`declare`、进程替换 `<()` `>()`、正则捕获组、`compgen` 补全脚本。
- **性能**：大文件处理用 `awk` 而非循环；用 `mapfile` 代替 `while read`。
- **周边工具**：`jq`（处理 JSON）、`yq`（YAML）、`fzf`（模糊查找）、`tmux`、`parallel`（GNU 并行）。
- **何时该换语言**：当逻辑复杂（>300 行、复杂数据结构、需要第三方库）时，改用 Python/Go。
  Shell 的甜蜜点是**编排命令、文本流、系统胶水**，不是复杂算法。

---

## 附录：一页速查表

```bash
# 变量与引用
s="值"              echo "$s"          echo "${s}x"    # 花括号划边界
export V=1          readonly X=1       unset V

# 引号
'原样'   "解析$变量"   $'转义\n'

# 特殊参数
$0  $#  $1 $2  "$@"  "$*"  $?  $$  $RANDOM  $LINENO

# 参数扩展（s="Hello-World"）
${#s}       # 11         长度
${s/a/b}    # 替换第一个
${s//a/b}   # 替换全部
${s#*-}     # World      删最短前缀
${s##*/}    # 取文件名    删最长前缀
${s%-*}     # Hello      删最短后缀
${s%%-*}    # Hello      删最长后缀
${s:0:5}    # Hello      子串
${s:-默认}  # 默认值

# 命令 / 算术
now=$(date)            echo $((3+4))

# 调试三板斧
set -x            # 追踪执行
shellcheck x.sh   # 静态检查
bash -u x.sh      # 未定义变量报错

# 健壮三件套
set -euo pipefail

# 安全临时文件
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT

# 文本统计
sort file | uniq -c | sort -rn | head

# 前 10 大文件
du -ah . | sort -rh | head -10

# 找并处理（安全版）
find . -name "*.log" -print0 | xargs -0 -I{} rm -f {}

# 并发执行
for f in *; do (process "$f") & done; wait

# 字符串判断
[[ -z "$s" ]] && echo 空
[[ -n "$s" ]] && echo 非空
[[ "$s" == pat* ]] && echo 前缀匹配
[[ "$s" =~ ^[0-9]+$ ]] && echo 纯数字
```

---

## 三条贯穿始终的铁律

1. **要看变量的值，几乎总是加双引号**：`"$var"`。
2. **循环参数用 `"$@"`**。
3. **`=` 两边不加空格。**

只要这三条不违反，90% 的低级错误都不会出现。
