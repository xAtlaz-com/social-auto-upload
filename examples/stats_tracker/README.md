# Stats Tracker API 文档

社交媒体数据采集模块，支持抖音和小红书数据采集。

## 功能概述

- **大盘数据**：账号整体数据（粉丝数、总播放、总互动等）
- **视频/笔记列表**：所有作品的基础数据
- **每日播放趋势**：每个视频的每天播放增量（抖音）
- **每小时播放曲线**：24h 内新视频的小时级播放数据（抖音）

## 快速开始

### CLI 使用

```bash
# 抖音 - 完整数据
python -m examples.stats_tracker.cli --platform douyin

# 抖音 - 快速模式（不获取趋势）
python -m examples.stats_tracker.cli --platform douyin --no-trends

# 小红书
python -m examples.stats_tracker.cli --platform xhs

# 保存到文件
python -m examples.stats_tracker.cli --platform douyin --out data.json
```

### Python 调用

```python
import asyncio
from examples.stats_tracker import StatsCollector

async def main():
    # 采集抖音数据
    result = await StatsCollector.collect("douyin")
    
    # 快速模式（不获取趋势）
    result = await StatsCollector.collect("douyin", with_trends=False)
    
    # 采集小红书数据
    result = await StatsCollector.collect("xhs")
    
    # 获取 JSON
    json_str = result.to_json()
    
    # 保存到文件
    result.save("output.json")
    
    # 获取扁平化记录（适合导入飞书多维表格）
    records = result.get_flat_records()
    
    # 获取趋势记录
    trend_records = result.get_trend_records()

asyncio.run(main())
```

## API 参考

### StatsCollector.collect()

```python
async def collect(platform: str, with_trends: bool = True) -> CollectResult
```

**参数**
- `platform`: 平台名称，可选值：`"douyin"` | `"xiaohongshu"` | `"xhs"`
- `with_trends`: 是否获取趋势数据（仅抖音支持，默认 True）

**返回值**
- `CollectResult` 对象

---

## 数据结构

### CollectResult

采集结果的顶层对象。

```json
{
  "platform": "douyin",
  "collect_time": "2025-12-29 18:00:00",
  "success": true,
  "message": "ok",
  "video_count": 10,
  "account_stats": { ... },
  "videos": [ ... ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `platform` | string | 平台：`douyin` / `xiaohongshu` |
| `collect_time` | string | 采集时间 `YYYY-MM-DD HH:MM:SS` |
| `success` | bool | 是否成功 |
| `message` | string | 状态消息 |
| `video_count` | int | 视频/笔记数量 |
| `account_stats` | object | 大盘数据 |
| `videos` | array | 视频/笔记列表 |

**方法**
- `to_json(indent=2)` → `str`: 转为 JSON 字符串
- `to_dict()` → `dict`: 转为字典
- `save(filepath)`: 保存到文件
- `get_flat_records()` → `List[dict]`: 获取扁平化记录（每视频一行）
- `get_trend_records()` → `List[dict]`: 获取趋势记录（每数据点一行）

---

### account_stats（大盘数据）

#### 抖音

```json
{
  "follower_count": 12345,
  "total_play": 100000,
  "total_like": 5000,
  "total_comment": 200,
  "total_share": 100,
  "avg_play_per_video": 10000,
  "avg_like_per_video": 500,
  "avg_comment_per_video": 20,
  "avg_share_per_video": 10
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `follower_count` | int | 粉丝数 |
| `total_play` | int | 总播放量 |
| `total_like` | int | 总点赞数 |
| `total_comment` | int | 总评论数 |
| `total_share` | int | 总分享数 |
| `avg_play_per_video` | int | 条均播放 |
| `avg_like_per_video` | int | 条均点赞 |
| `avg_comment_per_video` | int | 条均评论 |
| `avg_share_per_video` | int | 条均分享 |

#### 小红书

```json
{
  "follower_count": 5000,
  "following_count": 100,
  "total_note_count": 50,
  "total_view": 80000,
  "total_imp": 200000,
  "total_interact": 3000
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `follower_count` | int | 粉丝数 |
| `following_count` | int | 关注数 |
| `total_note_count` | int | 笔记总数 |
| `total_view` | int | 总观看数 |
| `total_imp` | int | 总曝光数 |
| `total_interact` | int | 总互动数 |

---

### VideoStats（视频/笔记数据）

#### 通用字段

```json
{
  "platform": "douyin",
  "video_id": "7339123456789",
  "title": "视频标题",
  "publish_time": "2025-12-28 10:00:00",
  "collect_time": "2025-12-29 18:00:00",
  "cover_url": "https://...",
  "like_count": 100,
  "comment_count": 20,
  "share_count": 5
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `platform` | string | 平台 |
| `video_id` | string | 视频/笔记 ID |
| `title` | string | 标题 |
| `publish_time` | string | 发布时间 |
| `collect_time` | string | 采集时间 |
| `cover_url` | string | 封面图 URL |
| `like_count` | int | 点赞数 |
| `comment_count` | int | 评论数 |
| `share_count` | int | 分享数 |

#### 抖音特有字段

```json
{
  "play_count": 12345,
  "avg_play_duration": 15.5,
  "completion_rate_5s": 0.85,
  "bounce_rate_2s": 0.1,
  "new_fans": 3,
  "daily_trend": [...],
  "hourly_trend": [...]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `play_count` | int | 播放量 |
| `avg_play_duration` | float | 平均播放时长（秒） |
| `completion_rate_5s` | float | 5秒完播率（0-1） |
| `bounce_rate_2s` | float | 2秒跳出率（0-1） |
| `new_fans` | int | 新增粉丝 |
| `daily_trend` | array | 每日播放趋势 |
| `hourly_trend` | array | 每小时播放趋势（仅新视频） |

#### 小红书特有字段

```json
{
  "imp_count": 50000,
  "view_count": 8000,
  "collect_count": 200,
  "click_rate": 0.16
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `imp_count` | int | 曝光量 |
| `view_count` | int | 观看量 |
| `collect_count` | int | 收藏数 |
| `click_rate` | float | 封面点击率（0-1） |

---

### TrendPoint（趋势数据点）

```json
{
  "date_time": "2025-12-28",
  "value": 5000
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `date_time` | string | 时间点。每日格式：`YYYY-MM-DD`，每小时格式：`YYYY-MM-DD HH:00:00` |
| `value` | int | 该时段的播放增量 |

**daily_trend 示例**
```json
[
  {"date_time": "2025-12-26", "value": 3000},
  {"date_time": "2025-12-27", "value": 5000},
  {"date_time": "2025-12-28", "value": 4345}
]
```

**hourly_trend 示例**（仅 24h 内新视频）
```json
[
  {"date_time": "2025-12-28 10:00:00", "value": 500},
  {"date_time": "2025-12-28 11:00:00", "value": 800},
  {"date_time": "2025-12-28 12:00:00", "value": 1200},
  ...
]
```

---

## 完整输出示例

### 抖音

```json
{
  "platform": "douyin",
  "collect_time": "2025-12-29 18:26:00",
  "success": true,
  "message": "ok",
  "video_count": 2,
  "account_stats": {
    "follower_count": 12345,
    "total_play": 100000,
    "total_like": 5000,
    "avg_play_per_video": 10000,
    "avg_like_per_video": 500
  },
  "videos": [
    {
      "platform": "douyin",
      "video_id": "7339123456789",
      "title": "这是一个测试视频",
      "publish_time": "2025-12-28 10:00:00",
      "collect_time": "2025-12-29 18:26:00",
      "cover_url": "https://p3.douyinpic.com/...",
      "play_count": 12345,
      "like_count": 100,
      "comment_count": 20,
      "share_count": 5,
      "avg_play_duration": 15.5,
      "completion_rate_5s": 0.85,
      "bounce_rate_2s": 0.1,
      "new_fans": 3,
      "daily_trend": [
        {"date_time": "2025-12-28", "value": 5000},
        {"date_time": "2025-12-29", "value": 7345}
      ],
      "hourly_trend": [
        {"date_time": "2025-12-28 10:00:00", "value": 500},
        {"date_time": "2025-12-28 11:00:00", "value": 800},
        {"date_time": "2025-12-28 12:00:00", "value": 1200}
      ]
    }
  ]
}
```

### 小红书

```json
{
  "platform": "xiaohongshu",
  "collect_time": "2025-12-29 18:26:00",
  "success": true,
  "message": "ok",
  "video_count": 2,
  "account_stats": {
    "follower_count": 5000,
    "total_view": 80000
  },
  "videos": [
    {
      "platform": "xiaohongshu",
      "video_id": "65f123abc",
      "title": "这是一篇小红书笔记",
      "publish_time": "2025-12-25 14:30:00",
      "collect_time": "2025-12-29 18:26:00",
      "cover_url": "https://sns-img.xhscdn.com/...",
      "imp_count": 50000,
      "view_count": 8000,
      "like_count": 300,
      "comment_count": 50,
      "collect_count": 200,
      "share_count": 30,
      "click_rate": 0.16,
      "daily_trend": [],
      "hourly_trend": []
    }
  ]
}
```

---

## 辅助方法

### get_flat_records()

获取扁平化记录，适合直接导入飞书多维表格或数据库。

```python
records = result.get_flat_records()
# [
#   {
#     "platform": "douyin",
#     "video_id": "7339...",
#     "title": "...",
#     "publish_time": "...",
#     "collect_time": "...",
#     "play_count": 12345,
#     "like_count": 100,
#     ...
#   },
#   ...
# ]
```

### get_trend_records()

获取趋势数据的扁平化记录，每个数据点一行。

```python
records = result.get_trend_records()
# [
#   {
#     "platform": "douyin",
#     "video_id": "7339...",
#     "title": "...",
#     "trend_type": "daily",
#     "date_time": "2025-12-28",
#     "value": 5000,
#     "collect_time": "..."
#   },
#   {
#     "platform": "douyin",
#     "video_id": "7339...",
#     "title": "...",
#     "trend_type": "hourly",
#     "date_time": "2025-12-28 10:00:00",
#     "value": 500,
#     "collect_time": "..."
#   },
#   ...
# ]
```

---

## 前置条件

1. **Cookie 文件**：需要先登录获取 cookie
   - 抖音：`cookies/douyin_uploader/account.json`
   - 小红书：`cookies/xiaohongshu_uploader/account.json`

2. **依赖安装**
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. **配置文件** `conf.py`
   ```python
   LOCAL_CHROME_PATH = "/path/to/chrome"  # 可选
   LOCAL_CHROME_HEADLESS = True           # 是否无头模式
   ```

---

## 注意事项

1. **趋势数据**
   - `daily_trend`: 所有视频都支持
   - `hourly_trend`: 仅 24h 内发布的新视频有数据

2. **采集速度**
   - 快速模式（`--no-trends`）：约 5-10 秒
   - 完整模式：取决于视频数量，每个视频约 3-5 秒

3. **数据时效**
   - 数据为采集时刻的快照
   - 建议定时采集存储，以便分析趋势

4. **小红书限制**
   - 小红书暂不支持时间趋势数据（API 限制）
   - `daily_trend` 和 `hourly_trend` 为空数组
