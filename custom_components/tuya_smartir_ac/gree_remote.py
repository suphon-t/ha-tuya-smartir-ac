# https://forum.mysensors.org/uploads/files/1469565493670-gree.pdf

from enum import Enum

class Mode(Enum):
  AUTO = 0x0
  COOL = 0x1
  DRY = 0x2
  FAN = 0x3
  HEAT = 0x4

class Fan(Enum):
  AUTO = 0x0
  LOW = 0x1
  MEDIUM = 0x2
  HIGH = 0x3

class VerticalVane(Enum):
  AUTO = 0x0
  FIX_HIGHEST = 0x2
  FIX_HIGH = 0x3
  FIX_MIDDLE = 0x4
  FIX_LOW = 0x5
  FIX_LOWEST = 0x6
  SWING_ALL = 0x1
  SWING_LOW = 0x7
  SWING_CENTER = 0x9
  SWING_HIGH = 0xb

class HorizontalVane(Enum):
  AUTO = 0x0
  FIX_LEFTMOST = 0x2
  FIX_LEFT = 0x3
  FIX_CENTER = 0x4
  FIX_RIGHT = 0x5
  FIX_RIGHTMOST = 0x6
  FIX_WIDE = 0xc
  SWING_ALL = 0x1
  SWING_SPREAD = 0xd

def enc_part(data, len):
  return bin(data)[2:].zfill(8)[::-1][:len]

def encode_gree_remote(mode=Mode.AUTO, power=False, fan=Fan.AUTO, temp=25, vertical_vane=VerticalVane.AUTO, horizontal_vane=HorizontalVane.AUTO):
  vertical_swing = vertical_vane == VerticalVane.SWING_ALL or vertical_vane == VerticalVane.SWING_LOW or vertical_vane == VerticalVane.SWING_CENTER or vertical_vane == VerticalVane.SWING_HIGH
  horizontal_swing = horizontal_vane == HorizontalVane.SWING_ALL or horizontal_vane == HorizontalVane.SWING_SPREAD
  swing = 1 if vertical_swing and horizontal_swing else 0
  sleep = 0
  timer = 0
  turbo = 0
  light = 1
  health = 0
  x_fan = 0
  scavenging = 0
  i_feel = 0

  byte_strings = []
  byte_strings.append(enc_part(mode.value, 3) + enc_part(1 if power else 0, 1) + enc_part(fan.value, 2) + enc_part(swing, 1) + enc_part(sleep, 1))
  byte_strings.append(enc_part(temp-16, 4) + enc_part(timer, 4))
  byte_strings.append(enc_part(0, 4) + enc_part(turbo, 1) + enc_part(light, 1) + enc_part(health, 1) + enc_part(x_fan, 1))
  byte_strings.append(enc_part(scavenging, 1) + enc_part(0, 3) + enc_part(0x5, 4))
  byte_strings.append(enc_part(0x2, 3) + enc_part(0, 5))

  byte_strings.append(enc_part(vertical_vane.value, 4) + enc_part(horizontal_vane.value, 4))
  byte_strings.append(enc_part(0, 2) + enc_part(i_feel, 1) + enc_part(0, 1) + enc_part(0x2, 4))
  byte_strings.append(enc_part(0, 8))

  bytes = [int(byte[::-1], 2) for byte in byte_strings]
  checksum = (0 + \
    (bytes[0] & 0x0F) + \
    (bytes[1] & 0x0F) + \
    (bytes[2] & 0x0F) + \
    (bytes[3] & 0x0F) + \
    ((bytes[5] & 0xF0) >> 4) + \
    ((bytes[6] & 0xF0) >> 4) + \
    ((bytes[7] & 0xF0) >> 4) + \
  10) & 0x0F
  byte_strings.append(enc_part(0, 4) + enc_part(checksum, 4))

  return {'byte_strings': byte_strings, **byte_strings_to_code(byte_strings)}

def byte_strings_to_code(byte_strings: list[str]):
  lengths = {
    '1': 1684,
    '0': 605,
    ' ': 20474,
  }
  codes = byte_strings[0]+byte_strings[1]+byte_strings[2]+byte_strings[3]+byte_strings[4][:3]+' '
  codes += byte_strings[5]+byte_strings[6]+byte_strings[7]+byte_strings[8]

  gaps = [lengths[i] for i in codes]
  pulses_and_gaps = [9211, 4605]
  for i in range(len(gaps)):
    pulses_and_gaps.append(lengths['0'])
    pulses_and_gaps.append(gaps[i])
  pulses_and_gaps.append(605)
  pulses_and_gaps.append(40947)

  return {'codes': codes, 'pulses': pulses_and_gaps}
