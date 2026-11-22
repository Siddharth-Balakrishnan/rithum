# Troubleshooting Guide

## 1. General debugging sequence

Use this order:

1. Reproduce the issue.
2. Record the exact command and complete error output.
3. Check whether the problem is configuration, Python code, Linux service, network, or physical hardware.
4. Inspect the narrowest relevant subsystem.
5. Make one change at a time.
6. Run the focused test.
7. Run the full test suite.
8. Record the root cause and fix.

Do not simultaneously change GPIO pins, power wiring, configuration, and Python code. That destroys the ability to isolate the fault.

## 2. Configuration command fails

Run:

```bash
source .venv/bin/activate
python -m core.config
```

Check:
- the full exception;
- environment variable spelling;
- numeric values;
- Boolean values;
- cross-field constraints;
- whether the expected virtual environment is active.

For a specific variable:

```bash
printf 'RITHUM_WEB_PORT=%s\n' "${RITHUM_WEB_PORT-<unset>}"
```

Do not print all environment variables into a public issue.

## 3. Unit tests fail

```bash
python -m unittest discover -s tests -v
```

Then isolate:

```bash
python -m unittest discover -s tests -p 'test_state_manager.py' -v
```

If a test calls a method with the wrong arguments, inspect the real method signature in source. Do not change production code merely to match an incorrect test.

## 4. Python imports the wrong environment

```bash
which python
python --version
python -m pip --version
```

Expected interpreter path should be under `~/projects/rithum/.venv/`.

Reactivate:

```bash
source .venv/bin/activate
```

Use `python -m pip`, not a bare `pip`, to ensure package installation targets the active interpreter.

## 5. GPIO device not found

```bash
gpiodetect
gpioinfo
ls -l /dev/gpiochip*
```

Check:
- kernel GPIO support;
- device nodes;
- permissions/group membership;
- libgpiod major API version;
- whether another process owns the line.

The project was set up against the libgpiod v2 API. Code written for the old v1 API may not work unchanged. Do not select GPIO lines until the physical pin map is reviewed.

## 6. Camera not detected

```bash
lsusb
v4l2-ctl --list-devices
ls -l /dev/video*
```

A Pi camera/ISP media node is not proof that a USB webcam is attached. Confirm the camera appears as a V4L2 device and inspect supported formats:

```bash
v4l2-ctl --list-formats-ext -d /dev/video0
```

Replace `/dev/video0` with the actual device.

## 7. Display or touchscreen not detected

```bash
ls -l /dev/dri/
ls /sys/class/drm/
cat /proc/bus/input/devices
lsusb
```

Check video output and touch input separately. HDMI can work while USB touch does not. USB touch can enumerate while the display panel remains unpowered.

Do not assume a generic 7-inch display uses the same resolution, orientation, touch controller, or power arrangement as another model.

## 8. Network or remote access issue

```bash
ip -br address
ip route
tailscale status
```

For a local listener:

```bash
ss -lntup
```

Check:
- service bind address;
- firewall;
- Wi-Fi/Ethernet state;
- Tailscale connectivity;
- application authentication;
- certificate/tunnel status if applicable.

A reachable host does not imply the application is healthy or that the user is authorized.

## 9. systemd service fails

For a known service unit:

```bash
systemctl status <unit-name> --no-pager
journalctl -u <unit-name> -b --no-pager
```

General failed units:

```bash
systemctl --failed
```

The initial machine inventory showed a failed `fwupd-refresh.service`. That was an OS maintenance-service issue and not evidence of a Rithum application failure. Re-check current status rather than assuming it remains failed.

## 10. Motor does not move

Do not begin by increasing PWM.

Check in order:
1. Physical E-stop released?
2. Motor power branch fused and powered?
3. Battery voltage measured and within operating range?
4. Driver logic supply present?
5. Driver enable state correct?
6. Pi-to-driver logic wiring correct?
7. Common ground requirements satisfied?
8. Correct channel and motor polarity?
9. Driver fault/thermal indicators?
10. Motor mechanically free?

Test with wheels raised and a low command. Stop if wiring, driver, or motor becomes hot or smells abnormal.

## 11. Motor moves in the wrong direction or wrong mecanum vector

- Verify physical wheel handedness and orientation.
- Verify each motor-to-channel mapping.
- Test one wheel at a time.
- Record positive motor direction.
- Verify the kinematic mixing matrix against the actual chassis.
- Do not fix a wiring error by layering arbitrary sign inversions across multiple modules.

## 12. Robot does not stop after controller disconnect

Treat this as a critical safety defect.

- Disconnect motor power using the physical isolation/E-stop.
- Do not continue driving.
- Inspect heartbeat reception, lease expiry, watchdog timing, worker state, and hardware disable behavior.
- Add regression tests for disconnect, stale command, and process crash.
- Do not consider a browser-side timeout sufficient.

## 13. Useful system snapshot

```bash
echo '=== OS ==='
uname -a
cat /etc/os-release

echo '=== PYTHON ==='
python --version
python -m pip --version

echo '=== STORAGE ==='
df -h /

echo '=== GPIO ==='
gpiodetect

echo '=== USB ==='
lsusb

echo '=== VIDEO ==='
v4l2-ctl --list-devices

echo '=== DISPLAY ==='
ls -l /dev/dri/ 2>/dev/null
ls /sys/class/drm/ 2>/dev/null

echo '=== NETWORK ==='
ip -br address

echo '=== SERVICES ==='
systemctl --failed
```

Remove serial numbers, machine IDs, private IP details if not needed, and credentials before sharing diagnostics publicly.
