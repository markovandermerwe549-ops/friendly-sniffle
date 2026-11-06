# Star Runner — C++ desktop edition

A native C++17 arcade game using raylib 5.5. Collect stars, avoid asteroids, and beat your saved high score. Includes a resizable window, pause, restart, and increasing difficulty. The browser version has been removed.

## Download

Open [Releases](https://github.com/markovandermerwe549-ops/friendly-sniffle/releases/latest) and expand **Assets**:

- **Windows 10/11 x64:** download `StarRunner-Windows-x64.zip`, extract it, and run `StarRunner.exe`.
- **Linux x64:** extract `StarRunner-Linux-x64.tar.gz` and run `./StarRunner`. Requires a graphical desktop, OpenGL 3.3, and glibc 2.35+ (Ubuntu 22.04 or newer).

Choose the named game archive. GitHub's automatic “Source code” archives contain source, not executables. The Windows build includes its C++ runtime statically and needs no raylib DLL.

Releases are published automatically after both Windows and Linux builds and tests succeed on each push to `main`. Follow progress under [Actions](https://github.com/markovandermerwe549-ops/friendly-sniffle/actions). The release workflow also supports **Run workflow**.

## Controls

- Arrows or WASD: move.
- Enter or the on-screen button: start, resume, restart.
- P or Escape: pause/resume.
- Close the window: quit.

Gold stars give 10 points; asteroids end the run. Losing window focus pauses play. Best scores are saved in the user's application data directory when writable.

## Build

Requires CMake 3.20+, Git, a C/C++17 toolchain, and internet access to fetch raylib on first configuration. Windows: Visual Studio 2022 with Desktop development with C++.

Ubuntu dependencies:

```sh
sudo apt-get install build-essential cmake git libasound2-dev libx11-dev libxrandr-dev libxi-dev libgl1-mesa-dev libglu1-mesa-dev libxcursor-dev libxinerama-dev
```

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel 2
ctest --test-dir build -C Release --output-on-failure
```

Run `build/Release/StarRunner.exe` on Windows or `build/StarRunner` on Linux. No external art assets required. For headless tests, add `-DBUILD_GAME=OFF` to configuration.

`src/game.hpp` contains gameplay; `src/main.cpp` handles rendering, input, and saves. `tests/game_test.cpp` checks movement, boundaries, collection, pause, collision, restart, and spawning. The workflow builds both platforms before publishing downloads. raylib uses its upstream zlib license.
