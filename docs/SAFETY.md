# Safety and Operational Constraints

## 1. Safety priority

Rithum is a moving machine. A Python exception, web disconnect, or incorrect state must not leave motor outputs energized.

The safety hierarchy is:

1. Physical emergency stop / hardware power interruption.
2. Critical hardware fault.
3. Obstacle safety layer (after sensors are integrated).
4. Operator lease and dead-man timeout.
5. Operating-mode policy.
6. User-interface behavior and animation.

A visual warning or software state label is not a physical safety mechanism.

## 2. Motor outputs disabled at boot

The configuration validator requires `motors_disabled_at_boot=True`. Preserve this invariant.

On startup:
- configure driver enable/output lines to a known disabled state before accepting commands;
- do not restore the previous movement command after a reboot;
- require a deliberate operator action to enter manual mode;
- verify the output-disable path before allowing motor power.

The current state manager does not perform GPIO initialization. The future supervisor/hardware layer must implement this behavior.

## 3. Emergency stop

The physical E-stop should interrupt motor power independently of the Pi, while allowing the Pi to remain powered for diagnostics where the power design permits.

Software handling:
1. Detect/receive the E-stop event.
2. Immediately command hardware motor disable.
3. Call `StateManager.emergency_stop(reason=...)`.
4. Reject further movement commands.
5. Require physical release confirmation.
6. Run safety checks.
7. Call `reset_safe_stop(safety_checks_passed=True)` only after those checks pass.

The E-stop latch must not be cleared merely because a client reconnects or sends a reset request.

## 4. Fault handling

A critical motor-driver, power, or safety-sensor fault should:
- disable motor outputs;
- call `report_fault(reason=...)`;
- record diagnostic details;
- reject movement commands;
- require fault clearance and safety checks;
- recover into `SELF_TEST`, never directly into active movement.

Do not silently clear a fault after a process restart.

## 5. Remote-control safety

The planned remote-control path requires:
- application authentication;
- authorization for control actions;
- one active operator lease;
- heartbeat/dead-man behavior;
- command range and freshness validation;
- stop on lease expiry or disconnect;
- server-side mode validation;
- no direct public GPIO/motor endpoint.

A network tunnel (including Tailscale or Cloudflare Tunnel/Access) is not a replacement for application authentication and authorization.

## 6. Electrical safety

- Pi GPIO is 3.3 V logic.
- Do not connect battery voltage, motor voltage, or 5 V/12 V sensor outputs directly to GPIO.
- Verify grounds, signal levels, and driver logic requirements from the actual datasheets.
- Fuse battery branches appropriately.
- Use wire gauge and connectors rated for expected current.
- Insulate exposed conductors and secure the battery.
- Use the correct charger for the actual cell count and chemistry.
- Do not charge a damaged, swollen, overheated, or unidentified battery pack.
- Do not work on exposed power wiring while the battery is connected.

## 7. Test procedure for motor changes

1. Disconnect motor power.
2. Inspect wiring and polarity.
3. Verify Pi/driver logic interface with a meter.
4. Confirm E-stop physically interrupts motor power.
5. Raise wheels clear of the floor.
6. Apply the lowest practical test command.
7. Test one motor channel at a time.
8. Confirm stop behavior and timeout behavior.
9. Test all four channels.
10. Lower the robot only after direction and stop behavior are confirmed.

Keep people, cables, and loose objects clear of wheels and rollers.

## 8. Autonomy gate

Autonomy is disabled by default. Do not enable it until:
- manual control is stable;
- all four IR sensors are installed and electrically verified;
- sensor placement and coverage are tested;
- stale/disconnected sensor behavior is defined as unsafe;
- obstacle response is tested at low speed;
- manual commands are also constrained by the obstacle-safety layer;
- the supervisor enforces mode and sensor-readiness checks;
- tests cover sensor failure and conflicting sensor readings.

The IR modules are not safety-rated. The robot must still be tested at low speed in a controlled environment.

## 9. Human interaction

Human presence or face detection must not grant movement authority. When entering human-interaction mode, the supervisor should stop movement and keep outputs disabled unless a separately reviewed interaction design explicitly permits a safe action.

## 10. Safety review checklist for pull requests

- [ ] Does the change preserve disabled outputs at boot?
- [ ] Can any error path leave outputs enabled?
- [ ] Does disconnect/timeout stop movement?
- [ ] Are all commands validated server-side?
- [ ] Are sensor failures treated as unknown/unsafe?
- [ ] Is E-stop independent of the Pi software?
- [ ] Are GPIO voltage levels safe?
- [ ] Are state transitions and recovery paths tested?
- [ ] Is autonomy still disabled unless the phase gate is satisfied?
