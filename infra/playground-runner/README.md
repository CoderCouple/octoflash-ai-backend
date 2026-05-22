# Playground Runner

The sandbox image for `/playground/render`. ManimGL inside a hardened
container — the **only** place in the codebase that executes user-supplied
Python.

## Build

```bash
make playground-image
# equivalent to:
#   docker build -t octoflash-playground-runner:latest infra/playground-runner
```

The image is large (~1.5 GB) because ManimGL pulls cairo, pango, freetype,
ffmpeg, and a full MESA software OpenGL stack — needed so the container
renders on any host without GPU passthrough.

## Security model

`PlaygroundService.render` invokes the image with:

| Flag                                    | Why                                        |
| --------------------------------------- | ------------------------------------------ |
| `--network=none`                        | No egress at all                           |
| `--user 1000:1000`                      | Non-root (`runner` in the image)           |
| `--memory 1g --cpus 1.0`                | RAM + CPU caps                             |
| `--pids-limit 128`                      | Fork-bomb defence                          |
| `--security-opt no-new-privileges`      | Block setuid escalation                    |
| `-v <job_dir>:/work`                    | Only the per-render dir is writable        |
| `--rm`                                  | Container + writable layer reclaimed       |
| host wall-clock timeout                 | Backstop if manimgl hangs                  |

The service also runs a cheap AST tripwire on the submitted code before it
hits the container. That's defence-in-depth, **not** the security boundary
— treat the container as the only thing standing between user code and the
host.

## Tuning

- `PLAYGROUND_DOCKER_IMAGE`         — image tag (defaults to `octoflash-playground-runner:latest`)
- `PLAYGROUND_TIMEOUT_SECONDS`      — host wall-clock cap (default 120s)
- `PLAYGROUND_MEMORY_LIMIT`         — `--memory` value (default `1g`)
- `PLAYGROUND_CPU_LIMIT`            — `--cpus` value (default `1.0`)
- `PLAYGROUND_PIDS_LIMIT`           — `--pids-limit` value (default `128`)

If you swap the base image (e.g. to a GPU-enabled one or one with extra
fonts / LaTeX bundles), keep the non-root user `1000:1000` and the working
directory `/work` so PlaygroundService keeps working unmodified.
