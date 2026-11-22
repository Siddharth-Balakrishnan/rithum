# Hardware and Integration Notes

## 1. Purpose and caution

This document records the current bill of materials and integration assumptions. It is not a wiring diagram. Verify each component's actual label, datasheet, pinout, and revision before connecting it.

The Raspberry Pi GPIO header uses 3.3 V logic. A sensor or driver output that can reach 5 V, 12 V, or battery voltage must not be connected directly to a Pi GPIO input.

## 2. Current bill of materials

| Subsystem | Component | Model/specification | Quantity |
|---|---|---|---:|
| Compute | Raspberry Pi | Pi 5, 8 GB | 1 |
| Drive | DC geared motors | OG555, 12 V, 100 RPM | 4 |
| Motor control | Dual-channel driver | Cytron MDD10A | 2 |
| Wheels | Mecanum wheels | 100 mm, left/right handed set | 4 |
| Feedback | Magnetic encoders | OE-37, two-channel | 2 |
| Main power | Li-ion battery | 14.8 V nominal, 10 Ah, 4S | 1 |
| Charging | Battery charger | 16.8 V, 5 A, 4S Li-ion | 1 |
| Voice | Smart speaker | Amazon Echo Dot 5th generation | 1 |
| Display | Touchscreen | 7-inch; listed resolution 1200 × 700 | 1 |
| Obstacle sensing | IR sensors | Four units; exact model TBD | 4 |
| Vision | USB webcam | Target budget ≤ ₹1,500 | 1 |
| Pi supply | Regulated USB-C source | Target Pi 5 input capability; exact bank TBD | 1 |

## 3. Drive system

Four OG555 12 V 100 RPM motors drive four mecanum wheels. Two Cytron MDD10A dual-channel drivers provide four independent motor channels.

Before powering the drive system:

- Confirm the driver board's exact revision and terminal labels.
- Confirm motor polarity and channel assignment.
- Confirm motor stall current from a reliable datasheet or measurement.
- Confirm the driver's continuous and peak ratings under the actual cooling and ambient conditions.
- Fit appropriately rated fuses and wiring.
- Verify that the battery/BMS can safely supply the combined load.
- Keep the wheels raised for first tests.
- Provide a physical means to interrupt motor power independently of the Pi.

The BOM lists approximately 4.134 A full-load current for each motor. Four motors at that value represent about 16.5 A combined. This is only a rough load estimate, not a safe fuse or battery design value. Startup/stall current can be materially higher and must be measured or sourced from the motor datasheet.

The MDD10A is listed as 10 A continuous per channel. Do not interpret a peak rating as a continuous operating rating.

## 4. Mecanum wheel arrangement

The set includes two left-handed and two right-handed wheels. Correct orientation is essential. Mark each wheel and motor position before assembly.

A common four-wheel layout uses front-left (FL), front-right (FR), rear-left (RL), and rear-right (RR). The exact roller orientation and motor polarity must be verified on the physical chassis. Do not copy a motor sign matrix from another chassis without validating it.

Calibration procedure:

1. Raise the chassis so no wheel touches the ground.
2. Label all four motor channels.
3. Apply a very low duty-cycle pulse to one channel at a time.
4. Record wheel rotation direction.
5. Confirm left/right wheel handedness.
6. Validate forward and reverse at low speed.
7. Validate lateral movement.
8. Validate rotation in place.
9. Only then test on the floor in a clear, controlled area.

## 5. Motor drivers and Pi interface

The Pi sends low-voltage logic/control signals to the driver. The motor supply comes from the battery/power distribution system, not from the Pi GPIO pins.

- Never power a motor from a Pi GPIO.
- Never feed the 14.8 V battery into a Pi GPIO or 5 V rail.
- Confirm driver logic input voltage compatibility.
- Confirm common-ground requirements from the driver documentation.
- Use a regulated supply for the Pi.
- Keep motor-current wiring physically separated from sensitive signal wiring where practical.
- Use strain relief and secure connectors.

The exact GPIO pin map is not finalized. Do not invent pin numbers in application code. Store verified mappings in configuration only after the wiring plan is reviewed.

## 6. Encoders

Two OE-37 encoders are available. They are optional testing instrumentation and do not need to remain connected in the initial UI-controlled movement phase.

The supplied BOM describes two-channel A/B quadrature outputs. Verify the actual encoder output voltage and interface circuitry. Do not assume the encoder can be connected directly to the Pi simply because its supply range includes a voltage compatible with another subsystem.

Document:
- which motors have encoders;
- encoder supply voltage;
- output voltage;
- counts per revolution as actually measured;
- whether the count figure is motor-shaft or output-shaft based;
- signal conditioning and GPIO pins.

## 7. IR obstacle sensors

Four IR sensors are intended for obstacle detection and avoidance, not line following. The intended placement is front-left, front-right, rear-left, and rear-right, with mounting angle finalized through physical testing.

The exact model is not selected in the current project record. Before purchase or connection, verify:

- digital or analog output;
- active-high or active-low behavior;
- supply voltage;
- output voltage and output stage (push-pull/open-collector);
- detection range and target-material limitations;
- ambient-light sensitivity;
- adjustment method;
- response time;
- mounting geometry.

If an output can exceed 3.3 V, use a suitable level-shifting/interface circuit. Cheap IR modules are not safety-rated and must not be treated as the only collision-prevention mechanism.

## 8. Power architecture

The design uses a 14.8 V nominal 4S battery for the motor/power distribution system and a separate regulated supply/power bank for the Raspberry Pi and display where practical.

Important:
- A fully charged 4S Li-ion pack is approximately 16.8 V, not 14.8 V.
- Never connect the battery directly to the Pi 5 USB-C input.
- Use a DC-DC converter with the correct output voltage/current and suitable thermal margin for any battery-fed auxiliary load.
- Pi 5 power requirements depend on attached USB/display loads. Check the exact supply profile and cable capability; a headline wattage alone does not prove 5 V/5 A capability.
- The touchscreen may require its own power budget. Do not assume the Pi can power it safely.
- The Echo Dot 5 supply in the supplied BOM is listed as 12 V, 1.25 A (15 W). If powering it from the main battery, use a regulated 12 V converter rated with appropriate continuous-current margin. Never connect it directly to the 4S battery.
- The battery BMS is not a substitute for correct fusing, wiring, charger compatibility, or a safe enclosure.

## 9. Display

The planned display is a 7-inch touchscreen, listed as 1200 × 700, connected over HDMI for video and USB for touch/power depending on the actual model.

Before configuring the display stack, confirm:
- exact manufacturer and model;
- native resolution and refresh rate;
- HDMI connector/cable requirements;
- USB touch controller identification;
- whether USB carries touch only or also power;
- total current draw;
- supported rotation/orientation.

A 1080p TV was planned for an early HDMI test. That test should not be treated as validation of the final touchscreen.

## 10. Camera

A USB webcam is planned for later human-presence/face detection. The initial Pi inventory did not show a USB camera. When connected, inspect:

```bash
lsusb
v4l2-ctl --list-devices
ls -l /dev/video*
```

Check supported formats and frame rates before selecting OpenCV capture settings.

## 11. Hardware inventory commands

```bash
# USB devices
lsusb

# GPIO chips and lines
gpiodetect
gpioinfo

# Video devices
v4l2-ctl --list-devices
ls -l /dev/video*

# Display/GPU devices
ls -l /dev/dri/
ls /sys/class/drm/

# Input devices, including touch
cat /proc/bus/input/devices

# Network interfaces
ip -br address
```

Capture command output with date, kernel version, and the physical device revision. Do not publish hardware serial numbers or machine IDs in public issue reports.
