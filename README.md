# 🤖 Vicon Robot

A wheelchair-mounted robotic arm that grabs objects using Vicon motion capture for localization. An LLM agent or a TUI operator selects targets, and the system collects synchronized trajectory + camera data for VLA model finetuning.

## Architecture

Five components communicate via Redis:

```
┌─────────┐    vicon_objects     ┌─────────┐  robot_command_channel  ┌──────────────────┐  trajectory_events  ┌─────────────┐
│  Vicon   │ ─────────────────►  │   TUI   │ ─────────────────────►  │ Robot Controller │ ──────────────────► │   Camera    │
│  Tracker │  (Redis key, 10Hz)  │         │   (Redis pubsub)        │                  │  (Redis pubsub)     │  Recorder   │
└─────────┘                      └─────────┘                         └──────────────────┘                     └─────────────┘
                                      ▲                                       ▲
                                      │                                       │
                                 ┌─────────┐  robot_command_channel           │
                                 │   LLM   │ ─────────────────────────────────┘
                                 │  Agent   │
                                 └─────────┘
```

| Component | Runtime | Role |
|-----------|---------|------|
| **Vicon Tracker** | conda, Python 3.12 | Tracks object positions via motion capture, publishes to Redis |
| **LLM Agent** | conda, Python 3.12 | Autonomous mode — uses GPT to pick targets and send grab commands |
| **Robot TUI** | uv, Python 3.11+ | Manual mode — operator picks targets from a live table |
| **Robot Controller** | conda, Python 3.7 | Executes grab sequences on the AUBO i5, logs joint trajectories |
| **Camera Recorder** | uv, Python 3.11+ | Captures RGB frames synchronized with robot movements |

All inter-process communication goes through **Redis** (pubsub + key-value).

## Project Structure

```
vicon-robot/
├── vicon/                  # Vicon motion capture tracker
├── llm/                    # LLM agent (autonomous commands)
├── robot_tui/              # TUI operator interface
├── robot_controller/       # AUBO i5 robot control + trajectory logging
├── robot_camera/           # RGB camera capture for VLA data
└── data/                   # 📂 Collected trajectories + frames
    └── trajectories/
```

## 🚀 Getting Started

### Prerequisites

- Docker (for Redis)
- conda (for vendor SDK environments: `vicon`, `robot`)
- [uv](https://docs.astral.sh/uv/) (for TUI and camera packages)

### Startup

Start each component in a separate terminal, in this order:

**0. Redis**

```bash
docker run -d --name redis -p 6379:6379 redis
```

**1. Vicon Tracker** — publishes object positions to Redis

```bash
cd vicon
conda activate vicon
python main.py
```

> ✅ Wait until you see "Base" detected — other components need this offset.

**2. Robot Controller** — listens for grab commands

```bash
cd robot_controller
conda activate robot
python main.py
```

> ✅ You should see `=== Listening for robot commands... ===`

**3. Camera Recorder** — captures frames during grabs

```bash
cd robot_camera
uv run robot-camera --device 0 --fps 5 --preview
```

> ✅ Live preview window shows "IDLE - waiting for trajectory".
>
> Use `--device 1` if your USB camera isn't device 0. Drop `--preview` for headless.

**4. TUI** (or LLM Agent) — sends grab commands

```bash
# Manual mode
cd robot_tui
uv run robot-tui

# OR autonomous mode
cd llm
conda activate llm
python main.py
```

> ✅ TUI shows a table of tracked objects. Select one and press `g` to grab.

### Shutdown

Press `q` in the TUI, `q` in the camera preview (or Ctrl+C), then Ctrl+C for the rest.

```bash
docker stop redis
```

## 🎬 Grab Sequence

When a grab command is sent (from TUI or LLM):

```
TUI / LLM                   Robot Controller              Camera Recorder
 │                                │                              │
 ├─► grab_object command ────────►│                              │
 │                                ├─► trajectory "start" ───────►│ 📷 begin recording
 │                                ├─► phase "move_to_grab" ─────►│ 📷 capturing...
 │                                │   (robot arm moving)         │ 📷 capturing...
 │                                ├─► phase "lift_object" ──────►│ 📷 capturing...
 │                                ├─► phase "move_to_return" ───►│ 📷 capturing...
 │                                ├─► phase "return_home" ──────►│ 📷 capturing...
 │                                ├─► trajectory "end" ─────────►│ 📷 stop recording
 │                                │                              │
 │                                │   saves trajectory CSV       │   saves JPEGs + metadata
```

## 📂 Data Format

Each grab produces a pair of outputs in `data/trajectories/`:

```
data/trajectories/
├── trajectory_20260130_143022_123456.csv       # joint angles, poses, gripper (50Hz)
└── 20260130_143022_123456_frames/              # RGB frames (5Hz)
    ├── 000000.jpg
    ├── 000001.jpg
    ├── ...
    └── metadata.jsonl                          # timestamp + phase per frame
```

Both use `time.time()` timestamps. Align by nearest timestamp in post-processing for VLA training data.

## 💡 Tips

- **No robot hardware?** TUI and camera still run — commands just won't execute. Useful for testing the pipeline end-to-end.
- **No camera?** Robot controller works standalone. Trajectory CSVs still get saved.
- **Restarting a component?** Just restart it. Everything reconnects through Redis.
- **Finding camera devices:** `python -c "import cv2; [print(f'Device {i}') for i in range(5) if cv2.VideoCapture(i).isOpened()]"`
