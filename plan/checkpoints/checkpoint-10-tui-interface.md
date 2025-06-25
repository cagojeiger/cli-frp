# Checkpoint 10: k9s 스타일 TUI 인터페이스

## Status: 📋 Planned
This checkpoint is planned but not yet implemented.
Priority may change based on K8s integration progress.

## 개요
k9s의 직관적인 인터페이스와 Textual 프레임워크를 결합하여 FRP 터널을 시각적으로 관리할 수 있는 고급 TUI(Terminal User Interface)를 구현합니다. 실시간 모니터링, 키보드 기반 네비게이션, 그리고 풍부한 시각적 피드백을 제공합니다.

## 목표
- **k9s 스타일 UX**: 직관적인 키보드 네비게이션과 다중 뷰
- **실시간 모니터링**: 터널 상태, 트래픽, 로그의 라이브 업데이트
- **풍부한 시각화**: 컬러 코딩, 차트, 테이블, 진행 표시줄
- **접근성**: 마우스와 키보드 모두 지원
- **확장성**: 플러그인과 커스터마이징 지원

## k9s 디자인 패턴 적용

### 1. 다중 뷰 시스템
```
┌─ FRP Manager ─────────────────────────────────────────────────────────┐
│ Context: production-server    Namespace: all    View: tunnels         │
├───────────────────────────────────────────────────────────────────────┤
│ ■ Tunnels  ● Logs  ◦ Stats  ◦ Config                                  │
├───────────────────────────────────────────────────────────────────────┤
│ NAME         LOCAL   PATH        STATUS   UPTIME    REQUESTS   BYTES  │
│ > myapp      3000    /myapp/     🟢 UP    2h 15m    1,234      45MB   │
│   api        8080    /api/v1/    🟢 UP    1h 30m    567        12MB   │
│   dev-site   5000    /dev/       🔴 DOWN  -         -          -      │
│   staging    4000    /staging/   🟡 WARN  45m       89         3MB    │
├───────────────────────────────────────────────────────────────────────┤
│ <s>tart <d>elete <l>ogs <r>estart <e>dit <q>uit                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 2. 컨텍스트 인식 액션
```python
# k9s와 동일한 패턴으로 리소스별 액션 정의
BINDINGS = {
    "tunnels": [
        ("s", "start_tunnel", "Start"),
        ("d", "delete_tunnel", "Delete"),
        ("l", "view_logs", "Logs"),
        ("r", "restart_tunnel", "Restart"),
        ("e", "edit_tunnel", "Edit"),
    ],
    "logs": [
        ("f", "follow_logs", "Follow"),
        ("c", "clear_logs", "Clear"),
        ("s", "save_logs", "Save"),
    ]
}
```

### 3. 명령어 모드
```
> tunnel create --port 3000 --path /myapp
> logs myapp --follow
> stats --interval 5s
> config server production-server.com
```

## TUI 화면 구성

### 메인 대시보드
```
┌─ FRP Dashboard ───────────────────────────────────────────────────────┐
│                                                                       │
│ 🔗 Active Tunnels: 3        📊 Total Requests: 1,890                 │
│ 🟢 Healthy: 2              ⬆️  Uptime: 2h 15m                        │
│ 🔴 Errors: 1               💾 Data Transfer: 60.5 MB                  │
│                                                                       │
│ ┌─ Quick Stats ─────────┐  ┌─ Recent Activity ──────────────────────┐ │
│ │ Requests/min:    125   │  │ 14:30 myapp     GET /myapp/api/users   │ │
│ │ Avg Response:    89ms  │  │ 14:29 api       POST /api/v1/auth      │ │
│ │ Error Rate:      0.2%  │  │ 14:29 staging   GET /staging/health    │ │
│ │ Bandwidth:      5MB/s  │  │ 14:28 myapp     GET /myapp/dashboard    │ │
│ └───────────────────────┘  └─────────────────────────────────────────┘ │
│                                                                       │
│ ┌─ System Health ───────────────────────────────────────────────────┐ │
│ │ CPU:  ████████░░ 80%    Memory: ██████░░░░ 60%                    │ │
│ │ Disk: ███░░░░░░░ 30%    Network: ████████░░ 85%                   │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ <t>unnels <l>ogs <s>tats <c>onfig <h>elp <q>uit                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 터널 목록 뷰
```
┌─ Tunnel Management ───────────────────────────────────────────────────┐
│ Filter: [all_______________] Sort: name ↑  Refresh: 2s  Auto: ✓       │
├───────────────────────────────────────────────────────────────────────┤
│ NAME         LOCAL   PATH           STATUS    UPTIME     REQ/MIN  ERR  │
│ > myapp      3000    /myapp/        🟢 UP     2h 15m     125      0    │
│   api        8080    /api/v1/       🟢 UP     1h 30m     45       2    │
│   dev-site   5000    /dev/          🔴 DOWN   -          -        -    │
│   staging    4000    /staging/      🟡 RETRY  45m        12       1    │
│   websocket  9000    /ws/           🟢 UP     3h 22m     89       0    │
│   admin      8888    /admin/        🔒 AUTH   1h 45m     5        0    │
├───────────────────────────────────────────────────────────────────────┤
│ Details: myapp                                                        │
│ ├─ URL: https://example.com/myapp/                                     │
│ ├─ Local: http://localhost:3000                                       │
│ ├─ Started: 2024-01-15 12:15:30                                       │
│ ├─ Process ID: 12345                                                  │
│ ├─ Total Requests: 15,045                                             │
│ ├─ Total Data: 234.5 MB                                               │
│ └─ Last Activity: 2 seconds ago                                       │
├───────────────────────────────────────────────────────────────────────┤
│ <n>ew <s>tart <d>elete <r>estart <e>dit <l>ogs <i>nfo <q>uit <enter>  │
└───────────────────────────────────────────────────────────────────────┘
```

### 로그 뷰어
```
┌─ Logs: myapp ─────────────────────────────────────────────────────────┐
│ Filter: [error_____________] Lines: 1000  Follow: ✓  Wrap: ✓          │
├───────────────────────────────────────────────────────────────────────┤
│ 2024-01-15 14:30:15 [INFO ] Request: GET /myapp/api/users             │
│ 2024-01-15 14:30:15 [DEBUG] DB query: SELECT * FROM users LIMIT 50    │
│ 2024-01-15 14:30:15 [INFO ] Response: 200 OK (89ms)                   │
│ 2024-01-15 14:29:45 [ERROR] Connection timeout: 192.168.1.100         │
│ 2024-01-15 14:29:30 [INFO ] Request: POST /myapp/api/auth              │
│ 2024-01-15 14:29:30 [INFO ] User login: john@example.com               │
│ 2024-01-15 14:29:30 [INFO ] Response: 200 OK (156ms)                  │
│ 2024-01-15 14:29:15 [WARN ] Slow query detected: 2.3s                 │
│ 2024-01-15 14:28:45 [INFO ] Request: GET /myapp/dashboard              │
│ 2024-01-15 14:28:45 [INFO ] Response: 200 OK (45ms)                   │
│ │                                                                     │
│ ████████████████████████████████████████████████ [following logs...] │
├───────────────────────────────────────────────────────────────────────┤
│ <c>lear <s>ave <f>ilter <w>rap toggle <t>unnels <q>uit                │
└───────────────────────────────────────────────────────────────────────┘
```

### 통계 대시보드
```
┌─ Statistics Dashboard ────────────────────────────────────────────────┐
│ Period: Last 1 hour  Interval: 5 min  Auto-refresh: ✓                │
├───────────────────────────────────────────────────────────────────────┤
│ ┌─ Request Rate ──────────────────┐ ┌─ Response Time ─────────────────┐ │
│ │ 200 ┤                           │ │ 500ms ┤                         │ │
│ │ 180 ┤     ▁▄▆█                  │ │ 400ms ┤   ▄▆                   │ │
│ │ 160 ┤   ▃▅███                   │ │ 300ms ┤ ▁▃██▄                  │ │
│ │ 140 ┤ ▂▄██████                  │ │ 200ms ┤▃█████▃                 │ │
│ │ 120 ┤▁███████▆                  │ │ 100ms ┤██████▁▂               │ │
│ │   0 └─────────────────────────  │ │   0ms └─────────────────────── │ │
│ │     12:00  12:30  13:00  13:30  │ │       12:00  12:30  13:00      │ │
│ └─────────────────────────────────┘ └─────────────────────────────────┘ │
│                                                                       │
│ ┌─ Error Distribution ──────────┐   ┌─ Top Endpoints ─────────────────┐ │
│ │ 4xx Errors: 23 (1.2%)         │   │ /myapp/api/users     1,245 req  │ │
│ │ 5xx Errors: 5  (0.3%)         │   │ /myapp/dashboard      789 req   │ │
│ │ Timeouts:   12 (0.6%)         │   │ /api/v1/auth          567 req   │ │
│ │ Success:    1,860 (98.9%)      │   │ /myapp/static/       456 req   │ │
│ └────────────────────────────────┘   │ /staging/health       234 req   │ │
│                                      └─────────────────────────────────┘ │
│                                                                       │
│ ┌─ Bandwidth Usage ─────────────────────────────────────────────────┐ │
│ │ In:  ████████░░ 8.5 MB/s   Out: ██████░░░░ 6.2 MB/s             │ │
│ │ Peak In: 12.3 MB/s at 13:15   Peak Out: 9.8 MB/s at 13:20       │ │
│ └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ <r>efresh <e>xport <p>eriod <t>unnels <q>uit                          │
└───────────────────────────────────────────────────────────────────────┘
```

### 설정 화면
```
┌─ Configuration ───────────────────────────────────────────────────────┐
│                                                                       │
│ ┌─ Server Settings ──────────────────────────────────────────────────┐ │
│ │ Address: [example.com________________]                              │ │
│ │ Port:    [7000____]                                                │ │
│ │ Token:   [************************____] 🔒                        │ │
│ │ Timeout: [30______] seconds                                        │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─ Default Settings ─────────────────────────────────────────────────┐ │
│ │ ☑ Auto-start tunnels on app launch                                │ │
│ │ ☑ Show QR codes for URLs                                           │ │
│ │ ☑ Open browser automatically                                       │ │
│ │ ☐ Enable mouse support                                             │ │
│ │ ☑ Color output                                                     │ │
│ │ Refresh interval: [2___] seconds                                   │ │
│ │ Log level: [INFO____▼]                                             │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─ Appearance ───────────────────────────────────────────────────────┐ │
│ │ Theme: [dark_____▼] (dark, light, auto)                           │ │
│ │ Color scheme: [default_▼] (default, nord, dracula)                │ │
│ │ Font size: [normal__▼] (small, normal, large)                     │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─ Security ─────────────────────────────────────────────────────────┐ │
│ │ ☑ Require confirmation for deletions                              │ │
│ │ ☑ Save logs to file                                               │ │
│ │ ☐ Enable remote management API                                     │ │
│ │ API Port: [8999____]                                               │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ <s>ave <r>eset <t>est connection <c>ancel <q>uit                      │
└───────────────────────────────────────────────────────────────────────┘
```

## Textual 기반 구현 아키텍처

### 파일 구조
```
src/frp_wrapper/
├── tui/
│   ├── __init__.py
│   ├── app.py              # 메인 TUI 애플리케이션
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── dashboard.py    # 메인 대시보드
│   │   ├── tunnels.py      # 터널 관리 화면
│   │   ├── logs.py         # 로그 뷰어
│   │   ├── stats.py        # 통계 대시보드
│   │   └── config.py       # 설정 화면
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── tunnel_table.py # 터널 목록 테이블
│   │   ├── log_viewer.py   # 로그 뷰어 위젯
│   │   ├── charts.py       # 차트 위젯들
│   │   ├── status_bar.py   # 상태 표시줄
│   │   └── qr_code.py      # QR 코드 위젯
│   ├── styles/
│   │   ├── main.tcss       # 메인 스타일시트
│   │   ├── dark.tcss       # 다크 테마
│   │   └── light.tcss      # 라이트 테마
│   └── utils/
│       ├── keybindings.py  # 키보드 바인딩
│       ├── formatters.py   # 데이터 포맷터
│       └── themes.py       # 테마 관리
```

### 핵심 컴포넌트

**1. 메인 애플리케이션 (app.py)**
```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer
from .screens import DashboardScreen, TunnelsScreen, LogsScreen, StatsScreen, ConfigScreen

class FRPManagerApp(App):
    """k9s 스타일 FRP 터널 매니저."""

    CSS_PATH = "styles/main.tcss"
    TITLE = "FRP Manager"

    BINDINGS = [
        Binding("1", "show_dashboard", "Dashboard", priority=True),
        Binding("2", "show_tunnels", "Tunnels", priority=True),
        Binding("3", "show_logs", "Logs", priority=True),
        Binding("4", "show_stats", "Stats", priority=True),
        Binding("5", "show_config", "Config", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("h,?", "help", "Help"),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "tunnels": TunnelsScreen,
        "logs": LogsScreen,
        "stats": StatsScreen,
        "config": ConfigScreen,
    }

    def on_mount(self) -> None:
        """앱 시작 시 대시보드 화면으로 이동."""
        self.push_screen("dashboard")

    def action_show_dashboard(self) -> None:
        self.switch_screen("dashboard")

    def action_show_tunnels(self) -> None:
        self.switch_screen("tunnels")

    # ... 기타 액션들
```

**2. 터널 테이블 위젯 (tunnel_table.py)**
```python
from textual.widgets import DataTable
from textual.reactive import reactive
from rich.text import Text
from typing import List, Dict, Any

class TunnelTable(DataTable):
    """k9s 스타일 터널 목록 테이블."""

    tunnels: reactive[List[Dict[str, Any]]] = reactive([])

    def on_mount(self) -> None:
        """테이블 컬럼 설정."""
        self.add_columns(
            "NAME", "LOCAL", "PATH", "STATUS",
            "UPTIME", "REQ/MIN", "ERRORS"
        )
        self.cursor_type = "row"
        self.zebra_stripes = True

    def watch_tunnels(self, tunnels: List[Dict[str, Any]]) -> None:
        """터널 데이터 변경 시 테이블 업데이트."""
        self.clear()
        for tunnel in tunnels:
            status_text = self._format_status(tunnel["status"])
            self.add_row(
                tunnel["name"],
                str(tunnel["local_port"]),
                tunnel["path"],
                status_text,
                tunnel["uptime"],
                str(tunnel["requests_per_min"]),
                str(tunnel["errors"]),
                key=tunnel["name"]
            )

    def _format_status(self, status: str) -> Text:
        """상태에 따른 컬러 포맷팅."""
        status_colors = {
            "running": ("🟢", "green"),
            "stopped": ("🔴", "red"),
            "error": ("🟡", "yellow"),
            "starting": ("🔵", "blue"),
        }
        icon, color = status_colors.get(status, ("⚪", "white"))
        return Text(f"{icon} {status.upper()}", style=color)
```

**3. 실시간 로그 뷰어 (log_viewer.py)**
```python
from textual.widgets import RichLog
from textual.reactive import reactive
from textual.worker import work
import asyncio

class LogViewer(RichLog):
    """실시간 로그 스트리밍 위젯."""

    tunnel_name: reactive[str] = reactive("")
    follow_logs: reactive[bool] = reactive(True)

    def watch_tunnel_name(self, tunnel_name: str) -> None:
        """터널 변경 시 로그 스트림 재시작."""
        if tunnel_name:
            self.clear()
            self.start_log_stream(tunnel_name)

    @work(exclusive=True)
    async def start_log_stream(self, tunnel_name: str) -> None:
        """백그라운드에서 로그 스트리밍."""
        # ProcessManager에서 로그 스트림 가져오기
        async for log_line in self.get_tunnel_logs(tunnel_name):
            if self.follow_logs:
                timestamp, level, message = self.parse_log_line(log_line)
                self.write(self.format_log_line(timestamp, level, message))
                if self.follow_logs:
                    self.scroll_end()
```

**4. 차트 위젯 (charts.py)**
```python
from textual.widget import Widget
from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text
from rich.table import Table
import time
from collections import deque

class SparklineChart(Widget):
    """간단한 스파크라인 차트."""

    def __init__(self, title: str, max_points: int = 60):
        super().__init__()
        self.title = title
        self.data = deque(maxlen=max_points)
        self.max_value = 1

    def add_data_point(self, value: float) -> None:
        """데이터 포인트 추가."""
        self.data.append(value)
        self.max_value = max(self.max_value, max(self.data))
        self.refresh()

    def render(self) -> RenderResult:
        """스파크라인 렌더링."""
        if not self.data:
            return Text("No data")

        # 유니코드 블록 문자로 차트 생성
        chart_chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        chart_line = ""

        for value in self.data:
            normalized = value / self.max_value if self.max_value > 0 else 0
            char_index = int(normalized * (len(chart_chars) - 1))
            chart_line += chart_chars[char_index]

        table = Table.grid()
        table.add_row(f"{self.title}: {chart_line}")
        return table

class ProgressRing(Widget):
    """CPU/메모리 사용률 링 차트."""

    def __init__(self, label: str, value: float = 0.0):
        super().__init__()
        self.label = label
        self.value = value

    def render(self) -> RenderResult:
        """원형 진행률 표시."""
        filled_chars = int(self.value * 10)
        empty_chars = 10 - filled_chars

        bar = "█" * filled_chars + "░" * empty_chars
        percentage = f"{self.value * 100:.1f}%"

        return Text(f"{self.label}: {bar} {percentage}")
```

### 키보드 바인딩 시스템

**컨텍스트별 키바인딩 (keybindings.py)**
```python
from textual.binding import Binding
from typing import Dict, List

class KeyBindings:
    """k9s 스타일 컨텍스트별 키바인딩."""

    GLOBAL_BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("h,?", "help", "Help"),
        Binding("1", "show_dashboard", "Dashboard"),
        Binding("2", "show_tunnels", "Tunnels"),
        Binding("3", "show_logs", "Logs"),
        Binding("4", "show_stats", "Stats"),
        Binding("5", "show_config", "Config"),
    ]

    CONTEXT_BINDINGS = {
        "tunnels": [
            Binding("n", "new_tunnel", "New"),
            Binding("d", "delete_tunnel", "Delete"),
            Binding("s", "start_tunnel", "Start"),
            Binding("x", "stop_tunnel", "Stop"),
            Binding("r", "restart_tunnel", "Restart"),
            Binding("e", "edit_tunnel", "Edit"),
            Binding("l", "view_logs", "Logs"),
            Binding("i", "tunnel_info", "Info"),
            Binding("enter", "tunnel_details", "Details"),
        ],
        "logs": [
            Binding("f", "toggle_follow", "Follow"),
            Binding("c", "clear_logs", "Clear"),
            Binding("s", "save_logs", "Save"),
            Binding("w", "toggle_wrap", "Wrap"),
            Binding("/", "filter_logs", "Filter"),
        ],
        "stats": [
            Binding("e", "export_stats", "Export"),
            Binding("p", "change_period", "Period"),
            Binding("i", "change_interval", "Interval"),
        ]
    }
```

### 테마 시스템

**메인 스타일시트 (main.tcss)**
```css
/* k9s 스타일 전역 테마 */
Screen {
    background: $background;
    color: $text;
}

/* 헤더 스타일 */
Header {
    dock: top;
    background: $primary;
    color: $text-on-primary;
    content-align: center middle;
}

/* 푸터 키바인딩 표시 */
Footer {
    dock: bottom;
    background: $surface;
    color: $text-muted;
}

/* 테이블 스타일 */
DataTable {
    background: $surface;
    color: $text;
    border: round $border;
}

DataTable > .datatable--header {
    background: $primary-container;
    color: $on-primary-container;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $secondary;
    color: $on-secondary;
}

/* 상태별 색상 */
.status-running {
    color: $success;
}

.status-stopped {
    color: $error;
}

.status-warning {
    color: $warning;
}

/* 차트 스타일 */
.chart {
    border: round $border;
    padding: 1;
    margin: 1;
}

/* 로그 뷰어 */
RichLog {
    border: round $border;
    background: $surface-variant;
    scrollbar-background: $outline;
    scrollbar-color: $primary;
}
```

**다크 테마 (dark.tcss)**
```css
/* k9s 다크 테마 */
:root {
    --background: #1e1e2e;
    --surface: #313244;
    --surface-variant: #45475a;
    --primary: #89b4fa;
    --primary-container: #74c7ec;
    --secondary: #cba6f7;
    --text: #cdd6f4;
    --text-muted: #6c7086;
    --text-on-primary: #11111b;
    --success: #a6e3a1;
    --warning: #f9e2af;
    --error: #f38ba8;
    --border: #585b70;
    --outline: #6c7086;
}
```

### 실시간 데이터 업데이트

**데이터 바인딩과 워커 (app.py)**
```python
from textual.reactive import reactive
from textual.worker import work
import asyncio

class FRPManagerApp(App):
    # 반응형 데이터
    tunnels: reactive[List[Dict]] = reactive([])
    system_stats: reactive[Dict] = reactive({})
    logs: reactive[List[str]] = reactive([])

    def on_mount(self) -> None:
        """앱 시작 시 데이터 수집 시작."""
        self.start_data_collection()

    @work(exclusive=True)
    async def start_data_collection(self) -> None:
        """백그라운드에서 지속적인 데이터 수집."""
        while True:
            # 터널 상태 업데이트
            self.tunnels = await self.collect_tunnel_data()

            # 시스템 통계 업데이트
            self.system_stats = await self.collect_system_stats()

            await asyncio.sleep(2)  # 2초마다 갱신

    async def collect_tunnel_data(self) -> List[Dict]:
        """터널 데이터 수집."""
        # ProcessManager를 통해 터널 정보 수집
        tunnel_data = []
        for tunnel in self.get_active_tunnels():
            tunnel_data.append({
                "name": tunnel.name,
                "local_port": tunnel.local_port,
                "path": tunnel.path,
                "status": tunnel.get_status(),
                "uptime": tunnel.get_uptime(),
                "requests_per_min": tunnel.get_request_rate(),
                "errors": tunnel.get_error_count(),
            })
        return tunnel_data
```

### 명령어 모드 구현

**명령어 파서 (command_parser.py)**
```python
from textual.widgets import Input
from textual.message import Message
from typing import Dict, Callable, Any

class CommandInput(Input):
    """k9s 스타일 명령어 입력."""

    class CommandSubmitted(Message):
        def __init__(self, command: str, args: Dict[str, Any]):
            self.command = command
            self.args = args
            super().__init__()

    def __init__(self, commands: Dict[str, Callable]):
        super().__init__(placeholder="Enter command...")
        self.commands = commands

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """명령어 파싱 및 실행."""
        command_line = event.value.strip()
        if not command_line:
            return

        parts = command_line.split()
        command = parts[0]
        args = self.parse_args(parts[1:])

        self.post_message(self.CommandSubmitted(command, args))
        self.clear()

    def parse_args(self, args: List[str]) -> Dict[str, Any]:
        """명령어 인자 파싱."""
        parsed = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--'):
                key = args[i][2:]
                if i + 1 < len(args) and not args[i + 1].startswith('--'):
                    parsed[key] = args[i + 1]
                    i += 2
                else:
                    parsed[key] = True
                    i += 1
            else:
                parsed.setdefault('positional', []).append(args[i])
                i += 1
        return parsed

# 명령어 핸들러들
COMMANDS = {
    "tunnel": {
        "create": lambda args: create_tunnel_dialog(args),
        "delete": lambda args: delete_tunnel(args.get('positional', [None])[0]),
        "start": lambda args: start_tunnel(args.get('positional', [None])[0]),
        "stop": lambda args: stop_tunnel(args.get('positional', [None])[0]),
    },
    "logs": {
        "clear": lambda args: clear_logs(),
        "save": lambda args: save_logs(args.get('file', 'logs.txt')),
        "filter": lambda args: filter_logs(args.get('pattern', '')),
    }
}
```

### QR 코드 위젯

**QR 코드 생성기 (qr_code.py)**
```python
from textual.widget import Widget
from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text
import qrcode
from io import StringIO

class QRCodeWidget(Widget):
    """터널 URL QR 코드 표시."""

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def render(self) -> RenderResult:
        """QR 코드를 ASCII 아트로 렌더링."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(self.url)
        qr.make(fit=True)

        # ASCII로 출력
        output = StringIO()
        qr.print_ascii(out=output)
        qr_text = output.getvalue()

        return Text(qr_text, style="white on black")
```

## 고급 기능

### 1. 플러그인 시스템
```python
# 플러그인 인터페이스
class FRPPlugin:
    """FRP Manager 플러그인 기본 클래스."""

    def __init__(self, app: FRPManagerApp):
        self.app = app

    def on_tunnel_created(self, tunnel: Dict) -> None:
        """터널 생성 시 호출."""
        pass

    def on_tunnel_status_changed(self, tunnel: Dict, old_status: str) -> None:
        """터널 상태 변경 시 호출."""
        pass

    def get_custom_widgets(self) -> List[Widget]:
        """커스텀 위젯 반환."""
        return []

# 예제 플러그인: Slack 알림
class SlackNotificationPlugin(FRPPlugin):
    def on_tunnel_status_changed(self, tunnel: Dict, old_status: str) -> None:
        if tunnel["status"] == "error" and old_status == "running":
            self.send_slack_alert(f"Tunnel {tunnel['name']} is down!")
```

### 2. 키보드 단축키 커스터마이징
```yaml
# ~/.frp-manager/keybindings.yaml
global:
  quit: ["q", "ctrl+c"]
  refresh: ["r", "f5"]
  help: ["h", "?", "f1"]

tunnels:
  new: ["n", "ctrl+n"]
  delete: ["d", "delete"]
  start: ["s", "space"]
  stop: ["x", "ctrl+x"]
  restart: ["r", "ctrl+r"]

logs:
  follow: ["f", "ctrl+f"]
  clear: ["c", "ctrl+l"]
  search: ["/", "ctrl+f"]
```

### 3. 성능 모니터링
```python
class PerformanceMonitor:
    """TUI 성능 모니터링."""

    def __init__(self):
        self.metrics = {
            "render_time": deque(maxlen=100),
            "update_frequency": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
        }

    def track_render_time(self, duration: float) -> None:
        self.metrics["render_time"].append(duration)

    def get_performance_stats(self) -> Dict[str, float]:
        return {
            "avg_render_time": sum(self.metrics["render_time"]) / len(self.metrics["render_time"]),
            "max_render_time": max(self.metrics["render_time"]),
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        }
```

## 배포 및 사용

### 패키지 설정
```toml
# pyproject.toml
[project.optional-dependencies]
tui = [
    "textual>=0.50.0",      # TUI 프레임워크
    "rich>=13.0",           # 터미널 출력
    "psutil>=5.9",          # 시스템 모니터링
]

[project.scripts]
cli-frpc = "frp_wrapper.cli.main:cli"
tui-frpc = "frp_wrapper.tui.app:main"
```

### 설치 및 실행
```bash
# CLI 및 TUI 모두 설치
pip install frp-wrapper[cli,tui]

# TUI 시작
tui-frpc

# 또는 직접 실행
python -m frp_wrapper.tui

# 특정 서버로 시작
tui-frpc --server example.com --token secret
```

### 설정 파일 지원
```yaml
# ~/.frp-manager/config.yaml
server:
  address: example.com
  port: 7000
  token: secret_token

appearance:
  theme: dark
  color_scheme: dracula
  mouse_support: true

refresh:
  interval: 2  # seconds
  auto_refresh: true

logging:
  level: INFO
  save_to_file: true
  file_path: ~/.frp-manager/logs/
```

이 TUI 인터페이스는 k9s의 직관적인 UX와 Textual의 강력한 기능을 결합하여, FRP 터널을 시각적이고 효율적으로 관리할 수 있는 도구를 제공합니다. 실시간 모니터링, 풍부한 시각화, 그리고 키보드 중심의 워크플로우로 개발자와 운영자 모두에게 최적의 경험을 선사합니다.
