# LY Memory Palace 记忆宫殿 

## 功能介绍 | Feature Overview

### English

**LY Memory Palace** is an AI long-term memory system that simulates human brain memory mechanisms. As an OpenClaw Skill, it gives AI assistants persistent cross-session memory — remembering your preferences, habits, and important decisions instead of starting from scratch every conversation.

#### Core Features

- **Three-Layer Memory Architecture**
  - 🧠 **Semantic Memory**: Stores facts, knowledge, and preferences. Decays very slowly, like how you remember "the sun rises in the east"
  - 📅 **Episodic Memory**: Stores specific events and decisions. Naturally decays over time, like gradually forgetting what you had for lunch last Tuesday
  - ⚙️ **Procedural Memory**: Stores operational habits and workflows. Strengthens with use, like becoming more skilled at riding a bicycle

- **Hippocampus Index & Associative Recall**
  - Each memory is indexed by keywords, functioning like the brain's hippocampus
  - When you mention related topics, the AI automatically "recalls" relevant memories
  - Memories form an association network: recalling one memory activates related ones (A→B→C spreading)

- **Ebbinghaus Forgetting Curve**
  - Memory strength naturally decays over time
  - Accessed/recalled memories are automatically reinforced
  - Memories below a strength threshold are automatically "forgotten" (cleaned up) to prevent information overload

- **Intelligent Deduplication**
  - When storing similar content, the system detects duplicates and reinforces existing memories instead of creating redundant entries

- **Zero-Dependency Pure Python**
  - No third-party libraries required — uses only Python standard library
  - Data stored locally in JSON format, fully offline operation

#### Use Cases

| Scenario | Effect |
|----------|--------|
| Long-term project development | AI remembers your tech stack, architecture decisions, coding habits |
| Personal assistant | AI remembers your preferences, schedules, frequent contacts |
| Learning tutor | AI remembers your learning progress, weak areas, mastered knowledge |
| Team collaboration | AI remembers project specs, team conventions, task assignments |

---

## 安装 | Installation

将 `ly-memory-palace` 文件夹复制到 OpenClaw 的 `skills/` 目录即可。

Copy the `ly-memory-palace` folder into the OpenClaw `skills/` directory.

```
skills/
└── ly-memory-palace/
    ├── SKILL.md         ← AI 操作指令 (SOP for AI)
    ├── palace.py        ← 记忆引擎 (Memory Engine)
    ├── config.json      ← 配置参数 (Configuration)
    └── README.md        ← 本文件 (This file)
```

## 数据目录 | Data Directory

记忆数据自动存储在 `skills/ly-memory-palace/data/` 下：

Memory data is automatically stored under `skills/ly-memory-palace/data/`:

```
data/
├── memories.json              ← 记忆数据 (Memory data)
└── hippocampus_index.json     ← 海马体索引 (Hippocampus index)
```

## CLI 命令参考 | CLI Reference

```bash
# 唤醒记忆 | Recall memories
python palace.py recall "查询文本"

# 存入记忆 | Store memory
python palace.py store --layer semantic --keywords "k1,k2" --content "内容" --emotion important

# 列出记忆 | List memories
python palace.py list [--layer semantic] [--sort strength|recent] [--detail]

# 统计信息 | Statistics
python palace.py stats

# 删除记忆 | Remove memory
python palace.py remove --id <memory_id>

# 衰减清理 | Decay cleanup
python palace.py decay

# 导出备份 | Export backup
python palace.py export --file backup.json

# 导入记忆 | Import memories
python palace.py import --file backup.json
```
Feedback & Optimization

We welcome your feedback, suggestions, and bug reports to help improve this project.

Contact: 529293436@qq.com

What to share:

Bug reports or issues encountered
Feature requests or improvement suggestions
Performance optimization ideas
Usage scenarios or success stories
Your feedback helps make this better for everyone!

### 中文

**LY Memory Palace** 是一个模拟人类大脑记忆机制的 AI 长期记忆系统。作为 OpenClaw Skill，它让 AI 助手拥有跨会话的持久记忆能力——记住你的偏好、习惯和重要决策，而不是每次对话都从零开始。

#### 核心特性

- **三层记忆架构**
  - 🧠 **语义记忆**（Semantic）：存储事实、知识、偏好。衰减极慢，像你记住"太阳从东方升起"一样稳固
  - 📅 **情景记忆**（Episodic）：存储具体事件和决策。随时间自然衰减，像你逐渐淡忘上周二午饭吃了什么
  - ⚙️ **程序记忆**（Procedural）：存储操作习惯和工作流。越用越强，像你骑自行车越来越熟练

- **海马体索引 & 关联唤醒**
  - 每条记忆通过关键词建立索引，就像大脑的海马体
  - 当你说到相关话题时，AI 会自动"想起"相关记忆
  - 记忆之间有关联网络：唤醒一条记忆会连带激活关联记忆（A→B→C 扩散）

- **艾宾浩斯遗忘曲线**
  - 记忆强度随时间自然衰减
  - 被使用/唤醒的记忆会自动强化
  - 强度过低的记忆会被自动"遗忘"（清理），防止信息过载

- **智能去重**
  - 存入相似内容时，系统自动检测并强化已有记忆，而非重复存储

- **零依赖纯 Python**
  - 不需要安装任何第三方库，仅使用 Python 标准库
  - 数据以 JSON 格式本地存储，完全离线运行

#### 使用场景

| 场景 | 效果 |
|------|------|
| 长期项目开发 | AI 记住你的技术栈、架构决策、编码习惯 |
| 个人助理 | AI 记住你的偏好、日程安排、常用联系人 |
| 学习辅导 | AI 记住你的学习进度、薄弱环节、已掌握知识 |
| 团队协作 | AI 记住项目规范、团队约定、分工情况 |

---



## 许可 | License

MIT


