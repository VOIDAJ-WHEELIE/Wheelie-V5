import pygame
import math
import random

pygame.init()

WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wheelie Rider V5")

clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 50)
info = pygame.font.SysFont(None, 35)

# ---------------------------------------------------------------- colors
BLACK = (20, 20, 20)
WHITE = (255, 245, 230)
RED = (255, 90, 80)
YELLOW = (255, 220, 0)
SKIN = (255, 214, 170)

# ---------------------------------------------------------------- maps
MAPS = [
    {
        "name": "Sunset Hills",
        "below": (45, 30, 50),
        "asphalt": (62, 58, 72),
        "curb": (150, 140, 155),
        "edge": (235, 225, 215),
        "line": (255, 215, 80),
        "hud": (255, 245, 230),
        "hud_bottom": (255, 245, 230),
    },
    {
        "name": "Seaside Coast",
        "below": (238, 212, 150),
        "asphalt": (92, 94, 104),
        "curb": (222, 218, 208),
        "edge": (250, 250, 250),
        "line": (250, 250, 250),
        "hud": (15, 35, 75),
        "hud_bottom": (70, 45, 20),
    },
]

current_map = 0
current_bike = 0
ground_offset = 0

WHEEL_RADIUS = 28
bike_length = 120
ROAD_THICKNESS = 80
HORIZON = 380  # beach map: where the sea meets the sky
SAND_TOP = 495  # beach map: where the sand starts


def ground_height(x):
    wx = x + ground_offset
    if current_map == 0:
        # Sunset Hills: rolling hills
        return HEIGHT - 120 + math.sin(wx * 0.005) * 50 + math.sin(wx * 0.002) * 30
    # Seaside Coast: smooth, gentle road
    return HEIGHT - 130 + math.sin(wx * 0.0022) * 12 + math.sin(wx * 0.0007) * 18


def front_wheel_pos(rear_x, rear_y, tilt_deg):
    a = math.radians(-tilt_deg)
    return (
        rear_x + math.cos(a) * bike_length,
        rear_y + math.sin(a) * bike_length,
    )


def min_tilt_for_ground(rear_x, rear_y):
    # Finds the tilt at which the front wheel is exactly resting on the ground.
    lo, hi = -60.0, 90.0
    for _ in range(25):
        mid = (lo + hi) / 2
        fx, fy = front_wheel_pos(rear_x, rear_y, mid)
        diff = fy - (ground_height(fx) - WHEEL_RADIUS)
        if diff > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------- helpers
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def ip(p):
    return (int(p[0]), int(p[1]))


def add_sun(surface, x, y, r, core, glow_color, glow_r, strength):
    glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    for rr in range(glow_r, r, -6):
        k = (1 - (rr - r) / (glow_r - r)) ** 2
        pygame.draw.circle(
            glow, (*glow_color, int(strength * k) + 4), (glow_r, glow_r), rr
        )
    surface.blit(glow, (x - glow_r, y - glow_r))
    pygame.draw.circle(surface, core[0], (x, y), r)
    pygame.draw.circle(surface, core[1], (x, y), int(r * 0.74))


# ---------------------------------------------------------------- sky for each map (pre-rendered)
SUNSET_STOPS = [
    (0.00, (25, 18, 70)),
    (0.35, (110, 40, 115)),
    (0.65, (235, 100, 75)),
    (0.85, (255, 170, 80)),
    (1.00, (255, 215, 130)),
]


def sunset_color(t):
    for i in range(len(SUNSET_STOPS) - 1):
        t0, c0 = SUNSET_STOPS[i]
        t1, c1 = SUNSET_STOPS[i + 1]
        if t0 <= t <= t1:
            return lerp_color(c0, c1, (t - t0) / (t1 - t0))
    return SUNSET_STOPS[-1][1]


def make_sunset_sky():
    s = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        pygame.draw.line(s, sunset_color(y / (HEIGHT - 120)), (0, y), (WIDTH, y))

    random.seed(7)
    for _ in range(70):
        sx = random.randint(0, WIDTH)
        sy = random.randint(0, 220)
        b = random.randint(150, 255)
        s.set_at((sx, sy), (b, b, b))
        if random.random() < 0.25:
            pygame.draw.circle(s, (b, b, b), (sx, sy), 1)

    add_sun(
        s, 820, 440, 70,
        [(255, 235, 160), (255, 250, 210)],
        (255, 190, 90), 250, 70,
    )
    return s


def make_beach_sky():
    s = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        if y <= HORIZON:
            c = lerp_color((55, 140, 230), (165, 220, 250), y / HORIZON)
        else:
            c = lerp_color((25, 115, 195), (70, 195, 215), (y - HORIZON) / 120)
        pygame.draw.line(s, c, (0, y), (WIDTH, y))

    add_sun(
        s, 240, 115, 42,
        [(255, 250, 215), (255, 255, 240)],
        (255, 250, 200), 170, 90,
    )
    return s


sky_surfaces = [make_sunset_sky(), make_beach_sky()]

clouds = [
    (150, 130, 220, 34),
    (520, 210, 280, 40),
    (950, 110, 240, 36),
    (700, 300, 200, 28),
]


def draw_clouds(c_low, c_high, parallax, limit_y=9999):
    span = WIDTH + 500
    for cx, cy, cw, ch in clouds:
        if cy > limit_y:
            continue
        x = (cx - ground_offset * parallax) % span - 250
        pygame.draw.ellipse(screen, c_low, (x, cy, cw, ch))
        pygame.draw.ellipse(
            screen, c_high, (x + cw * 0.2, cy - ch * 0.5, cw * 0.55, ch)
        )


def draw_mountains(base_y, color, parallax, seed):
    pts = []
    for x in range(0, WIDTH + 20, 10):
        wx = x + ground_offset * parallax + seed * 500
        y = (
            base_y
            - 40
            - 45 * abs(math.sin(wx * 0.0035))
            - 15 * math.sin(wx * 0.011 + 1)
        )
        pts.append((x, y))
    pts.append((WIDTH, HEIGHT))
    pts.append((0, HEIGHT))
    pygame.draw.polygon(screen, color, pts)


# ---------------------------------------------------------------- beach scenery
def draw_sailboat():
    span = WIDTH + 300
    x = (900 - ground_offset * 0.03) % span - 150
    y = HORIZON + 22
    pygame.draw.polygon(
        screen, (250, 250, 250), [(x, y - 70), (x, y - 8), (x + 40, y - 8)]
    )
    pygame.draw.polygon(
        screen, (255, 120, 90), [(x - 4, y - 55), (x - 4, y - 8), (x - 30, y - 8)]
    )
    pygame.draw.polygon(
        screen,
        (120, 70, 40),
        [(x - 36, y - 6), (x + 46, y - 6), (x + 34, y + 6), (x - 26, y + 6)],
    )


def draw_waves():
    t = pygame.time.get_ticks() / 1000.0
    for row in range(7):
        y = HORIZON + 12 + row * 15
        for i in range(10):
            x = (i * 140 + row * 53 + t * (8 + row * 3)) % (WIDTH + 100) - 50
            pygame.draw.line(
                screen, (190, 235, 245), (x, y), (x + 20 + row * 4, y), 2
            )


def draw_sand():
    t = pygame.time.get_ticks() / 1000.0
    pygame.draw.rect(screen, (95, 205, 215), (0, SAND_TOP - 16, WIDTH, 20))
    pygame.draw.rect(screen, (240, 215, 155), (0, SAND_TOP, WIDTH, HEIGHT - SAND_TOP))
    pygame.draw.rect(screen, (222, 192, 132), (0, SAND_TOP, WIDTH, 8))
    pts = [
        (x, SAND_TOP - 6 + 3 * math.sin(x * 0.03 + t * 1.5))
        for x in range(0, WIDTH + 20, 10)
    ]
    pygame.draw.lines(screen, (255, 255, 255), False, pts, 3)


def draw_palm(sx, base_y, h, lean):
    top = (sx + lean, base_y - h)
    mid = (sx + lean * 0.25, base_y - h * 0.5)
    pts = [(sx, base_y), mid, top]
    pygame.draw.lines(screen, (95, 60, 35), False, pts, 10)
    pygame.draw.lines(screen, (130, 90, 52), False, pts, 6)
    for a in (-170, -135, -100, -60, -30, -5, 175):
        r = math.radians(a)
        m = (top[0] + math.cos(r) * 28, top[1] + math.sin(r) * 28 - 8)
        tip = (top[0] + math.cos(r) * 58, top[1] + math.sin(r) * 58 + 18)
        pygame.draw.lines(screen, (25, 115, 60), False, [top, m, tip], 7)
        pygame.draw.lines(screen, (65, 175, 85), False, [top, m, tip], 3)
    pygame.draw.circle(screen, (100, 65, 35), (int(top[0]) - 5, int(top[1]) + 6), 5)
    pygame.draw.circle(screen, (100, 65, 35), (int(top[0]) + 5, int(top[1]) + 7), 5)


def draw_umbrella(sx, base_y, color):
    top = (sx, base_y - 58)
    pygame.draw.line(screen, (240, 240, 240), (sx, base_y), top, 4)
    radius = 40
    n = 8
    for i in range(n):
        a0 = math.pi + math.pi * i / n
        a1 = math.pi + math.pi * (i + 1) / n
        p0 = (top[0] + math.cos(a0) * radius, top[1] + math.sin(a0) * radius * 0.6 + 8)
        p1 = (top[0] + math.cos(a1) * radius, top[1] + math.sin(a1) * radius * 0.6 + 8)
        c = color if i % 2 == 0 else (250, 250, 250)
        pygame.draw.polygon(screen, c, [(top[0], top[1] - 6), p0, p1])
    pygame.draw.rect(screen, color, (sx - 30, base_y + 2, 60, 9))


UMBRELLA_COLORS = [(230, 70, 70), (255, 190, 50), (60, 160, 230)]


def draw_beach_props():
    spacing = 380
    off = ground_offset * 0.85
    base = int(off // spacing)
    for k in range(base, base + 5):
        sx = k * spacing + 100 - off
        h = 125 + (k * 37) % 50
        lean = 18 if k % 2 == 0 else -18
        draw_palm(sx, 530, h, lean)
        ux = k * spacing + 270 - off
        draw_umbrella(ux, 536, UMBRELLA_COLORS[k % 3])


# ---------------------------------------------------------------- road drawing
def draw_road():
    style = MAPS[current_map]
    surface_pts = [(x, ground_height(x)) for x in range(0, WIDTH + 20, 10)]

    pygame.draw.polygon(
        screen, style["below"], surface_pts + [(WIDTH, HEIGHT), (0, HEIGHT)]
    )

    bottom_pts = [(x, y + ROAD_THICKNESS) for x, y in reversed(surface_pts)]
    pygame.draw.polygon(screen, style["asphalt"], surface_pts + bottom_pts)

    curb_bottom = [(x, y + 8) for x, y in reversed(surface_pts)]
    pygame.draw.polygon(screen, style["curb"], surface_pts + curb_bottom)

    pygame.draw.lines(
        screen, style["edge"], False, [(x, y + 16) for x, y in surface_pts], 3
    )

    for x in range(0, WIDTH, 4):
        wx = x + ground_offset
        if int(wx // 50) % 2 == 0:
            y1 = ground_height(x) + 48
            y2 = ground_height(x + 4) + 48
            pygame.draw.line(screen, style["line"], (x, y1), (x + 4, y2), 5)


# ================================================================ BIKES
def bike_point(rx, ry, a, lx, ly):
    """Bike-local coords (lx along the bike, ly up) -> screen coords.
    Origin is the rear wheel hub. a = angle of the bike axis in radians."""
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = math.sin(a), -math.cos(a)
    return (rx + lx * ux + ly * vx, ry + lx * uy + ly * vy)


def two_bone(hip, foot, length, bend_forward=True):
    """Simple 2-bone IK for the rider's legs and arms (local coords)."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    d = max(math.hypot(dx, dy), 0.001)
    ux, uy = dx / d, dy / d
    h = math.sqrt(max(0.0, length * length - (min(d, 2 * length) / 2) ** 2))
    px, py = -uy, ux
    if bend_forward:
        if px < 0:
            px, py = -px, -py
    else:
        if py > 0:
            px, py = -px, -py
    mx, my = (hip[0] + foot[0]) / 2, (hip[1] + foot[1]) / 2
    return (mx + px * h, my + py * h)


def bezier(p0, p1, p2, n=10):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def curve_tubes(P, p0, p1, p2, w, n=10):
    pts = [P(*q) for q in bezier(p0, p1, p2, n)]
    return [(pts[i], pts[i + 1], w) for i in range(n)]


def tube_set(tubes, fill, outline, pad=5):
    """tubes = list of (p1, p2, width). Outline pass first, then fill pass,
    so every joint merges together cleanly."""
    for p1, p2, w in tubes:
        pygame.draw.line(screen, outline, p1, p2, w + pad)
        r = (w + pad) // 2
        pygame.draw.circle(screen, outline, ip(p1), r)
        pygame.draw.circle(screen, outline, ip(p2), r)
    for p1, p2, w in tubes:
        pygame.draw.line(screen, fill, p1, p2, w)
        pygame.draw.circle(screen, fill, ip(p1), w // 2)
        pygame.draw.circle(screen, fill, ip(p2), w // 2)


WHEEL_STYLES = {
    "cartoon": dict(
        tire=(60, 65, 95), tire_w=7, line=(35, 45, 120), rim=(255, 200, 40),
        spoke=(50, 70, 170), spokes=12, spoke_w=1, knobs=False, disc=False,
        hub=(60, 90, 220),
    ),
    "enduro": dict(
        tire=(30, 30, 34), tire_w=9, line=(10, 10, 14), rim=(205, 210, 220),
        spoke=(80, 80, 90), spokes=20, spoke_w=1, knobs=True, disc=True,
        hub=(45, 45, 52),
    ),
    "cruiser": dict(
        tire=(28, 28, 28), tire_w=8, line=(10, 10, 10), rim=(180, 182, 190),
        spoke=(175, 178, 185), spokes=12, spoke_w=2, knobs=True, disc=False,
        hub=(150, 150, 158),
    ),
    "jumper": dict(
        tire=(28, 28, 30), tire_w=9, line=(10, 10, 12), rim=(220, 220, 228),
        spoke=(70, 70, 78), spokes=16, spoke_w=1, knobs=True, disc=True,
        hub=(50, 50, 58),
    ),
}


def draw_wheel(cx, cy, rot, w):
    c = (int(cx), int(cy))
    tw = w["tire_w"]
    if w["knobs"]:
        # knobby off-road tire: slightly smaller base ring + bumps around it
        base_r = WHEEL_RADIUS - 2
        pygame.draw.circle(screen, w["tire"], c, base_r, tw)
        n = 24
        for i in range(n):
            ang = rot + i * (2 * math.pi / n)
            kx = cx + math.cos(ang) * (base_r - 1)
            ky = cy + math.sin(ang) * (base_r - 1)
            pygame.draw.circle(screen, w["tire"], (int(kx), int(ky)), 3)
        inner = base_r - tw
    else:
        pygame.draw.circle(screen, w["tire"], c, WHEEL_RADIUS, tw)
        pygame.draw.circle(screen, w["line"], c, WHEEL_RADIUS, 2)
        inner = WHEEL_RADIUS - tw
        pygame.draw.circle(screen, w["line"], c, inner, 2)

    # rim
    pygame.draw.circle(screen, w["rim"], c, inner - 2, 2)

    # spokes (they spin as the bike moves)
    for i in range(w["spokes"]):
        ang = rot + i * (2 * math.pi / w["spokes"])
        ex = cx + math.cos(ang) * (inner - 3)
        ey = cy + math.sin(ang) * (inner - 3)
        pygame.draw.line(screen, w["spoke"], (cx, cy), (ex, ey), w["spoke_w"])

    # brake disc
    if w["disc"]:
        pygame.draw.circle(screen, (185, 190, 200), c, 10)
        pygame.draw.circle(screen, (60, 60, 68), c, 10, 2)
        pygame.draw.circle(screen, (110, 112, 120), c, 6, 1)

    # hub
    pygame.draw.circle(screen, w["hub"], c, 5)
    pygame.draw.circle(screen, w["line"], c, 5, 2)


RIDERS = {
    "cartoon": dict(
        hip=(32, 66), shoulder=(52, 110), head=(58, 128), seat=(31, 64),
        leg=42, arm=38, body=BLACK, helmet=None, head_color=YELLOW,
    ),
    "enduro": dict(
        hip=(32, 74), shoulder=(54, 116), head=(60, 134), seat=(31, 71),
        leg=46, arm=38, body=(45, 50, 62), helmet=(210, 45, 45), head_color=SKIN,
    ),
    "cruiser": dict(
        hip=(32, 68), shoulder=(52, 112), head=(58, 130), seat=(33, 64),
        leg=44, arm=38, body=BLACK, helmet=None, head_color=YELLOW,
    ),
    "jumper": dict(
        hip=(40, 80), shoulder=(58, 124), head=(64, 142), seat=(33, 58),
        leg=46, arm=38, body=(30, 30, 36), helmet=(40, 120, 230), head_color=SKIN,
    ),
}

SHOE = (225, 225, 232)


def lerp_pt(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


def rider_pose(r, e, dip):
    """Blend between the sitting pose (e=0) and standing on the seat (e=1).
    Everything is in bike-local coordinates. dip = how far the rider's
    knees/arms are absorbing a bump (pixels)."""
    sx, sy = r["seat"]
    st_hip = (sx - 8, sy + 46)
    st_sh = (sx + 24, sy + 62)
    st_head = (st_sh[0] + 8, st_sh[1] + 14)

    hip = lerp_pt(r["hip"], st_hip, e)
    sh = lerp_pt(r["shoulder"], st_sh, e)
    head = lerp_pt(r["head"], st_head, e)
    hip = (hip[0], hip[1] - dip)
    sh = (sh[0], sh[1] - dip)
    head = (head[0], head[1] - dip)

    foot_seat = (sx + 4, sy + 7)                       # planted on the saddle
    foot_back = (hip[0] - 74, hip[1] - 26)             # other leg stretched out behind
    return hip, sh, head, foot_seat, foot_back


def darker(c, k=0.65):
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k))


def draw_shoe(P, foot, color):
    pygame.draw.line(screen, color, P(foot[0] - 3, foot[1]), P(foot[0] + 9, foot[1]), 5)


def draw_rider(P, r, wheel_rot, bb, grip):
    e = stand_e
    hip, sh, head, foot_seat, foot_back = rider_pose(r, e, rider_dip)
    body = r["body"]

    pedal_a = pedal_position(bb, wheel_rot, 0.0)
    pedal_b = pedal_position(bb, wheel_rot, math.pi)

    foot_a = lerp_pt(pedal_a, foot_seat, e)   # near leg: pedal -> planted on the seat
    foot_b = lerp_pt(pedal_b, foot_back, e)   # far leg: pedal -> stretched out behind

    knee_a = two_bone(hip, foot_a, r["leg"], True)
    knee_b = lerp_pt(
        two_bone(hip, foot_b, r["leg"], True),
        two_bone(hip, foot_b, r["leg"], False),
        e,
    )
    elbow = two_bone(sh, grip, r["arm"], False)

    far = darker(body)
    # far leg first so it sits behind
    pygame.draw.line(screen, far, P(*hip), P(*knee_b), 6)
    pygame.draw.line(screen, far, P(*knee_b), P(*foot_b), 6)
    draw_shoe(P, foot_b, darker(SHOE, 0.75))

    # near leg, torso, arms
    pygame.draw.line(screen, body, P(*hip), P(*knee_a), 6)
    pygame.draw.line(screen, body, P(*knee_a), P(*foot_a), 6)
    draw_shoe(P, foot_a, SHOE)
    pygame.draw.line(screen, body, P(*hip), P(*sh), 7)
    pygame.draw.line(screen, body, P(*sh), P(*elbow), 5)
    pygame.draw.line(screen, body, P(*elbow), P(*grip), 5)

    hs = ip(P(*head))
    if r["helmet"]:
        pygame.draw.circle(screen, r["helmet"], hs, 18)
        face = ip(P(head[0] + 8, head[1] - 4))
        pygame.draw.circle(screen, r["head_color"], face, 8)
    else:
        pygame.draw.circle(screen, r["head_color"], hs, 16)


def rider_hit_points(rear_x, rear_y, tilt_deg, rider_key):
    """Points on the rider that would hit the road if the bike looped out."""
    a = math.radians(-tilt_deg)
    hip, sh, head, _, _ = rider_pose(RIDERS[rider_key], stand_e, 0)
    r = RIDERS[rider_key]
    head_r = 18 if r["helmet"] else 16
    return [
        (bike_point(rear_x, rear_y, a, *head), head_r),
        (bike_point(rear_x, rear_y, a, *sh), 7),
        (bike_point(rear_x, rear_y, a, *hip), 7),
    ]


def pedal_position(bb, wheel_rot, phase=0.0):
    crank = wheel_rot * 0.6 + phase
    return (bb[0] + math.cos(crank) * 13, bb[1] + math.sin(crank) * 13)


def draw_crank(P, bb, pedal_local, arm_color, pedal_color, outline):
    bb_s = P(*bb)
    pedal_s = P(*pedal_local)
    pygame.draw.line(screen, outline, bb_s, pedal_s, 5)
    pygame.draw.line(screen, arm_color, bb_s, pedal_s, 3)
    pygame.draw.circle(screen, pedal_color, ip(pedal_s), 4)
    pygame.draw.circle(screen, outline, ip(pedal_s), 4, 2)


# ---------------------------------------------------------------- bike 1: cartoon (original)
# Every bike function gets two point-makers:
#   P(lx, ly) = a point on the FRAME / rider (moves when the suspension compresses)
#   H(lx, ly) = a point on a WHEEL HUB (always stays with the wheels)
def bike_cartoon(P, H, wheel_rot):
    W = WHEEL_STYLES["cartoon"]
    draw_wheel(*H(0, 0), wheel_rot, W)
    draw_wheel(*H(bike_length, 0), wheel_rot, W)

    OUTLINE = (35, 45, 120)
    FRAME_GREEN = (120, 225, 50)
    SEAT_BLUE = (60, 90, 220)
    GRAY = (170, 175, 190)

    bb = (46, 0)
    seat_top = (30, 54)
    head_top = (104, 58)
    head_bot = (98, 42)

    tubes = [
        (H(0, 0), P(*bb), 5),
        (H(0, 0), P(*seat_top), 5),
        (P(*bb), P(*seat_top), 5),
        (P(*seat_top), P(*head_top), 5),
        (P(*bb), P(*head_bot), 5),
        (P(*head_bot), P(*head_top), 5),
        (P(*head_bot), H(bike_length, 0), 5),
    ]
    tube_set(tubes, FRAME_GREEN, OUTLINE, 5)

    bb_s = P(*bb)
    pygame.draw.circle(screen, GRAY, ip(bb_s), 9)
    pygame.draw.circle(screen, OUTLINE, ip(bb_s), 9, 2)

    pedal = pedal_position(bb, wheel_rot)
    draw_crank(P, bb, pedal, SEAT_BLUE, SEAT_BLUE, OUTLINE)

    pygame.draw.line(screen, OUTLINE, P(*seat_top), P(30, 62), 5)
    seat_a, seat_b = P(20, 64), P(42, 64)
    pygame.draw.line(screen, OUTLINE, seat_a, seat_b, 11)
    pygame.draw.line(screen, SEAT_BLUE, seat_a, seat_b, 6)

    stem = (108, 67)
    grip = (98, 73)
    pygame.draw.line(screen, OUTLINE, P(*head_top), P(*stem), 6)
    pygame.draw.line(screen, OUTLINE, P(*stem), P(*grip), 7)
    pygame.draw.line(screen, SEAT_BLUE, P(*stem), P(*grip), 3)
    pygame.draw.circle(screen, OUTLINE, ip(P(*stem)), 5)

    draw_rider(P, RIDERS["cartoon"], wheel_rot, bb, grip)


# ---------------------------------------------------------------- bike 2: full-suspension enduro
def bike_enduro(P, H, wheel_rot):
    W = WHEEL_STYLES["enduro"]
    draw_wheel(*H(0, 0), wheel_rot, W)
    draw_wheel(*H(bike_length, 0), wheel_rot, W)

    FRAME = (238, 240, 246)
    LINE = (22, 22, 28)
    DARK = (45, 45, 52)

    bb = (48, 2)
    seat_top = (36, 58)
    head_top = (103, 62)
    head_bot = (97, 44)

    # rear cassette + derailleur + chain (these stay with the rear wheel)
    pygame.draw.circle(screen, (70, 70, 78), ip(H(0, 0)), 8)
    pygame.draw.circle(screen, LINE, ip(H(0, 0)), 8, 2)
    pygame.draw.line(screen, DARK, H(0, 0), H(-4, -14), 4)
    pygame.draw.circle(screen, DARK, ip(H(-5, -16)), 4)
    pygame.draw.line(screen, DARK, H(0, 8), P(*bb), 2)
    pygame.draw.line(screen, DARK, H(-5, -14), P(48, -9), 2)

    # chainring
    bb_s = P(*bb)
    pygame.draw.circle(screen, DARK, ip(bb_s), 12)
    pygame.draw.circle(screen, (150, 152, 160), ip(bb_s), 6)

    # frame (the swingarm tubes are anchored to the rear hub, so they swing)
    tubes = [
        (H(0, 0), P(*bb), 5),               # chain stay
        (H(0, 0), P(40, 36), 5),            # seat stay
        (P(*bb), P(*seat_top), 6),          # seat tube
        (P(40, 50), P(*head_top), 6),       # top tube
        (P(*bb), P(*head_bot), 8),          # down tube
        (P(*head_bot), P(*head_top), 7),    # head tube
    ]
    tube_set(tubes, FRAME, LINE, 4)

    # rear shock: top is on the frame, bottom is on the swingarm, so it
    # visibly squashes and extends as the bike bounces
    top = P(41, 40)
    bot = H(56, 16)
    pygame.draw.line(screen, DARK, P(58, 13), bot, 5)  # linkage
    pygame.draw.line(screen, LINE, top, bot, 10)
    pygame.draw.line(screen, (85, 85, 95), top, bot, 6)
    mid = lerp_pt(top, bot, 0.45)
    pygame.draw.line(screen, (190, 192, 200), top, mid, 3)

    # fork: dark stanchions slide down into the light lowers
    pygame.draw.line(screen, LINE, P(104, 62), H(112, 31), 10)
    pygame.draw.line(screen, DARK, P(104, 62), H(112, 31), 6)
    pygame.draw.line(screen, LINE, H(112, 31), H(120, 0), 10)
    pygame.draw.line(screen, FRAME, H(112, 31), H(120, 0), 6)
    pygame.draw.line(screen, LINE, P(100, 58), P(108, 58), 7)  # crown

    pedal = pedal_position(bb, wheel_rot)
    draw_crank(P, bb, pedal, DARK, (60, 60, 68), LINE)

    # seat post + saddle
    pygame.draw.line(screen, LINE, P(*seat_top), P(32, 68), 5)
    sa, sb = P(20, 70), P(42, 71)
    pygame.draw.line(screen, LINE, sa, sb, 11)
    pygame.draw.line(screen, (60, 60, 68), sa, sb, 6)

    # riser handlebar
    pygame.draw.line(screen, LINE, P(*head_top), P(108, 66), 6)
    pygame.draw.line(screen, DARK, P(108, 66), P(110, 78), 5)
    pygame.draw.line(screen, DARK, P(110, 78), P(98, 80), 5)
    pygame.draw.line(screen, LINE, P(103, 79), P(96, 80), 8)

    draw_rider(P, RIDERS["enduro"], wheel_rot, bb, (98, 80))


# ---------------------------------------------------------------- bike 3: olive cruiser
def bike_cruiser(P, H, wheel_rot):
    W = WHEEL_STYLES["cruiser"]
    draw_wheel(*H(0, 0), wheel_rot, W)
    draw_wheel(*H(bike_length, 0), wheel_rot, W)

    OLIVE = (125, 155, 30)
    OLIVE_DARK = (62, 82, 15)
    METAL = (172, 175, 182)

    bb = (46, 0)
    head_top = (104, 58)
    head_bot = (98, 42)

    # chain + big chainring
    pygame.draw.line(screen, (105, 105, 110), H(0, 7), P(46, 15), 3)
    pygame.draw.line(screen, (105, 105, 110), H(0, -7), P(46, -15), 3)
    pygame.draw.line(screen, (215, 215, 220), H(0, 7), P(46, 15), 1)
    pygame.draw.line(screen, (215, 215, 220), H(0, -7), P(46, -15), 1)
    pygame.draw.circle(screen, (95, 95, 100), ip(H(0, 0)), 8)
    bb_s = P(*bb)
    pygame.draw.circle(screen, METAL, ip(bb_s), 15)
    pygame.draw.circle(screen, (110, 112, 118), ip(bb_s), 15, 2)
    pygame.draw.circle(screen, (110, 112, 118), ip(bb_s), 8, 2)

    # frame with the curved top tube
    tubes = [
        (H(0, 0), P(*bb), 6),                  # chain stay
        (H(0, 0), P(38, 50), 4),               # seat stay
        (P(*bb), P(38, 52), 5),                # seat tube
        (P(*bb), P(*head_bot), 7),             # down tube
        (P(*head_bot), P(*head_top), 7),       # head tube
        (P(*head_bot), H(bike_length, 0), 7),  # fork
    ]
    tubes += curve_tubes(P, head_top, (72, 28), (40, 48), 5, 10)  # swoopy top tube
    tube_set(tubes, OLIVE, OLIVE_DARK, 4)

    pedal = pedal_position(bb, wheel_rot)
    draw_crank(P, bb, pedal, METAL, (20, 20, 20), (30, 30, 30))

    # seat post + black cushy saddle
    pygame.draw.line(screen, METAL, P(38, 52), P(36, 62), 4)
    sa, sb = P(22, 64), P(44, 64)
    pygame.draw.line(screen, (15, 15, 15), sa, sb, 11)
    pygame.draw.circle(screen, (15, 15, 15), ip(sa), 5)
    pygame.draw.circle(screen, (15, 15, 15), ip(sb), 5)

    # handlebars
    pygame.draw.line(screen, (70, 70, 75), P(*head_top), P(108, 66), 5)
    pygame.draw.line(screen, (20, 20, 20), P(108, 66), P(102, 74), 6)
    pygame.draw.circle(screen, (20, 20, 20), ip(P(102, 74)), 4)

    draw_rider(P, RIDERS["cruiser"], wheel_rot, bb, (102, 74))


# ---------------------------------------------------------------- bike 4: dirt jumper
def bike_jumper(P, H, wheel_rot):
    W = WHEEL_STYLES["jumper"]
    draw_wheel(*H(0, 0), wheel_rot, W)
    draw_wheel(*H(bike_length, 0), wheel_rot, W)

    SILVER = (228, 230, 236)
    LINE = (70, 72, 82)
    DARK = (35, 35, 42)
    GOLD = (255, 195, 50)

    bb = (46, 2)
    seat_top = (36, 50)
    head_top = (106, 64)
    head_bot = (100, 46)

    # rear derailleur + chain
    pygame.draw.circle(screen, (60, 60, 68), ip(H(0, 0)), 7)
    pygame.draw.line(screen, DARK, H(0, 0), H(-4, -12), 4)
    pygame.draw.circle(screen, DARK, ip(H(-5, -14)), 4)
    pygame.draw.line(screen, DARK, H(0, 7), P(46, 11), 2)
    pygame.draw.line(screen, DARK, H(-5, -12), P(46, -9), 2)
    bb_s = P(*bb)
    pygame.draw.circle(screen, DARK, ip(bb_s), 11)
    pygame.draw.circle(screen, (150, 152, 160), ip(bb_s), 5)

    # frame
    tubes = [
        (H(0, 0), P(*bb), 5),              # chain stay
        (H(0, 0), P(38, 46), 5),           # seat stay
        (P(*bb), P(*seat_top), 6),         # seat tube
        (P(38, 46), P(*head_top), 6),      # top tube
        (P(*bb), P(*head_bot), 8),         # down tube
        (P(*head_bot), P(*head_top), 7),   # head tube
        (P(44, 24), P(82, 26), 4),         # gusset
    ]
    tube_set(tubes, SILVER, LINE, 4)

    # gold suspension fork: silver stanchions slide down into the gold lowers
    pygame.draw.line(screen, LINE, P(*head_top), H(112, 32), 10)
    pygame.draw.line(screen, SILVER, P(*head_top), H(112, 32), 6)
    pygame.draw.line(screen, (150, 110, 20), H(112, 32), H(120, 0), 10)
    pygame.draw.line(screen, GOLD, H(112, 32), H(120, 0), 6)

    pedal = pedal_position(bb, wheel_rot)
    draw_crank(P, bb, pedal, DARK, (40, 40, 46), LINE)

    # low saddle
    pygame.draw.line(screen, LINE, P(*seat_top), P(34, 56), 5)
    sa, sb = P(24, 58), P(42, 58)
    pygame.draw.line(screen, DARK, sa, sb, 9)

    # wide riser bars
    pygame.draw.line(screen, LINE, P(*head_top), P(108, 72), 6)
    pygame.draw.line(screen, DARK, P(108, 72), P(104, 88), 5)
    pygame.draw.line(screen, DARK, P(104, 88), P(98, 90), 5)
    pygame.draw.line(screen, (15, 15, 15), P(103, 89), P(96, 90), 8)

    draw_rider(P, RIDERS["jumper"], wheel_rot, bb, (99, 90))


# fork / shock = how many pixels of suspension travel each bike has
BIKES = [
    {"name": "Cartoon", "draw": bike_cartoon, "rider": "cartoon", "fork": 0, "shock": 0},
    {"name": "Enduro MTB", "draw": bike_enduro, "rider": "enduro", "fork": 14, "shock": 10},
    {"name": "Olive Cruiser", "draw": bike_cruiser, "rider": "cruiser", "fork": 0, "shock": 0},
    {"name": "Dirt Jumper", "draw": bike_jumper, "rider": "jumper", "fork": 12, "shock": 0},
]


def draw_bike(rear_x, rear_y, tilt_deg, wheel_rot):
    a = math.radians(-tilt_deg)
    spec = BIKES[current_bike]

    # how far the frame has sunk toward the wheels at the back / at the front
    drop_rear = shock_c * spec["shock"]
    drop_front = fork_c * spec["fork"]

    def H(lx, ly):
        # a point that stays with a wheel hub
        return bike_point(rear_x, rear_y, a, lx, ly)

    def P(lx, ly):
        # a point on the frame: sinks by an amount that blends rear -> front
        t = max(0.0, min(1.1, lx / 104.0))
        drop = drop_rear + (drop_front - drop_rear) * t
        return bike_point(rear_x, rear_y, a, lx, ly - drop)

    spec["draw"](P, H, wheel_rot)


# ---------------------------------------------------------------- physics settings
# Tweak these to change how the bike feels!
ENGINE_POWER = 0.30      # forward acceleration at low speed
MAX_SPEED = 30
ROLL_RESIST = 0.01       # constant rolling resistance
AIR_DRAG = 0.00008       # grows with speed squared
SLOPE_FORCE = 0.4        # how much hills speed you up / slow you down

THROTTLE_TORQUE = 0.17   # how hard the throttle pops the front wheel (lower = gentler)
THROTTLE_RAMP = 0.08     # how quickly the throttle "builds" (lower = smoother)
MAX_RISE_SPEED = 2.0     # fastest the front wheel can rise (degrees per frame)
GRAVITY_TORQUE = 0.12    # gravity pulling the bike back toward the ground
COM_ANGLE = 40           # centre of mass angle; balance point = 90 - this (50 deg)
TILT_DAMPING = 0.95      # rotation friction (lower = more damping)

# You only crash (loop out) when the rider's head, shoulders or hips hit the road.
LOOP_OUT_TILT = 175      # safety net: bike completely upside down

# Brake (gentler than before: it builds up smoothly instead of grabbing)
BRAKE_FORCE = 0.25       # how hard the brake slows you down
BRAKE_RAMP = 0.12        # how quickly the brake builds up (lower = softer)
BRAKE_PULL = 0.20        # how strongly braking pulls the front wheel down
BRAKE_DROP = 0.06        # braking: how fast the front drops (bigger = quicker)
BRAKE_MIN_DROP = 0.8     # braking: slowest descent speed (degrees per frame)
BRAKE_MAX_DROP = 3.5     # braking: fastest descent speed (degrees per frame)

# Suspension springs
SUSP_K = 0.12            # spring stiffness
SUSP_C = 0.30            # damping (higher = less bouncy)
STAND_SPEED = 0.12       # how fast you stand up / sit down

# ---------------------------------------------------------------- game state
speed = 0
distance = 0
best_distances = [0, 0]
wheel_rot = 0

bike_x = 300
tilt = 0.0
tilt_vel = 0.0
throttle_amt = 0.0
brake_amt = 0.0

# suspension state: compression 0 (fully extended) -> 1 (fully squashed)
fork_c, fork_v = 0.0, 0.0
shock_c, shock_v = 0.0, 0.0
prev_gy1 = prev_gy2 = 0.0

# standing on the seat
stand_on = False
stand_amt = 0.0
stand_e = 0.0      # eased version of stand_amt, used for drawing
rider_dip = 0.0    # rider absorbing bumps with knees / arms

crashed = False


def reset_run():
    global speed, distance, tilt, tilt_vel, ground_offset, wheel_rot, crashed
    global throttle_amt, brake_amt, fork_c, fork_v, shock_c, shock_v
    global prev_gy1, prev_gy2, stand_on, stand_amt, stand_e, rider_dip
    speed = 0
    distance = 0
    tilt = 0.0
    tilt_vel = 0.0
    throttle_amt = 0.0
    brake_amt = 0.0
    ground_offset = 0
    wheel_rot = 0
    crashed = False
    fork_c = fork_v = shock_c = shock_v = 0.0
    prev_gy1 = prev_gy2 = ground_height(bike_x)
    stand_on = False
    stand_amt = stand_e = 0.0
    rider_dip = 0.0


def step_spring(c, v, target, kick):
    v += -SUSP_K * (c - target) - SUSP_C * v + kick
    c += v
    if c > 1.0:            # bottomed out
        c = 1.0
        v = -abs(v) * 0.3
    elif c < 0.0:          # fully extended
        c = 0.0
        v = max(v, 0.0)
    return c, v


reset_run()

running = True

while running:

    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_r and crashed:
                reset_run()

            if event.key == pygame.K_x:
                current_map = (current_map + 1) % len(MAPS)
                reset_run()

            if event.key == pygame.K_t:
                current_bike = (current_bike + 1) % len(BIKES)

            if event.key == pygame.K_f and not crashed:
                stand_on = not stand_on

    keys = pygame.key.get_pressed()

    if not crashed:

        throttle = keys[pygame.K_RIGHT]
        brake = keys[pygame.K_LEFT]

        # smooth throttle / brake (they build up instead of snapping on)
        throttle_amt += ((1.0 if throttle else 0.0) - throttle_amt) * THROTTLE_RAMP
        brake_amt += ((1.0 if brake else 0.0) - brake_amt) * BRAKE_RAMP

        # ---- forward speed
        if throttle:
            speed += ENGINE_POWER * (1 - speed / (MAX_SPEED * 1.2))

        speed -= BRAKE_FORCE * brake_amt

        speed -= ROLL_RESIST + AIR_DRAG * speed * speed

        slope = (ground_height(bike_x + 10) - ground_height(bike_x - 10)) / 20
        speed += slope * SLOPE_FORCE

        speed = max(0, min(MAX_SPEED, speed))

        # where the front wheel would rest on the road right now
        rear_y_check = ground_height(bike_x) - WHEEL_RADIUS
        ground_tilt = min_tilt_for_ground(bike_x, rear_y_check)

        # ---- wheelie physics (angular velocity)
        # gravity pulls the front down below the balance point and
        # tips you over backwards once you pass it
        torque = -GRAVITY_TORQUE * math.cos(math.radians(tilt + COM_ANGLE))

        # acceleration pops the front wheel up (weaker at high speed)
        torque += THROTTLE_TORQUE * throttle_amt * (1 - speed / 60) * (1 - brake_amt)

        tilt_vel += torque
        tilt_vel *= TILT_DAMPING

        if brake_amt > 0.01:
            # braking eases the front wheel back down to the road:
            # the higher it is, the faster it drops, then it settles softly
            height = tilt - ground_tilt
            target = -min(BRAKE_MAX_DROP, max(BRAKE_MIN_DROP, height * BRAKE_DROP))
            tilt_vel += (target - tilt_vel) * BRAKE_PULL * brake_amt

        tilt_vel = min(tilt_vel, MAX_RISE_SPEED)
        tilt += tilt_vel

        # ---- move the world
        ground_offset += speed
        wheel_rot += speed / WHEEL_RADIUS

        distance += speed * 0.05
        best_distances[current_map] = max(best_distances[current_map], distance)

        # ---- front wheel landing on the road
        rear_y_check = ground_height(bike_x) - WHEEL_RADIUS
        ground_tilt = min_tilt_for_ground(bike_x, rear_y_check)

        impact_val = 0.0
        if tilt <= ground_tilt:
            impact = -tilt_vel
            impact_val = max(impact, 0.0)
            tilt = ground_tilt
            if impact > 2.0:
                speed *= 1 - min(0.02 * impact, 0.15)
                tilt_vel = impact * 0.25
            else:
                tilt_vel = max(tilt_vel, 0)

        # ---- suspension
        front_air = (tilt - ground_tilt) > 1.5

        gy = ground_height(bike_x)
        bump = max(-3.0, min(3.0, gy - 2 * prev_gy1 + prev_gy2))  # road curvature
        prev_gy2, prev_gy1 = prev_gy1, gy

        # fork: carries weight on the road, dives under braking, springs out in a wheelie
        fork_target = 0.0 if front_air else 0.15 + 0.45 * brake_amt * (0.3 + speed / MAX_SPEED)
        # shock: squats under power, takes the load in a wheelie
        shock_target = max(
            0.0,
            0.12 + 0.22 * throttle_amt + (0.25 if front_air else 0.0) - 0.1 * brake_amt,
        )

        fork_c, fork_v = step_spring(
            fork_c, fork_v, fork_target, impact_val * 0.05 - bump * 0.06
        )
        shock_c, shock_v = step_spring(
            shock_c, shock_v, shock_target, impact_val * 0.03 - bump * 0.06
        )

        # ---- crash: only when the rider actually hits the road
        if tilt > 45:
            for (px, py), radius in rider_hit_points(
                bike_x, ground_height(bike_x) - WHEEL_RADIUS, tilt,
                BIKES[current_bike]["rider"],
            ):
                if py + radius >= ground_height(px):
                    crashed = True

        if tilt > LOOP_OUT_TILT:
            crashed = True

    # ---- standing up on the seat (smooth transition)
    stand_amt += ((1.0 if stand_on else 0.0) - stand_amt) * STAND_SPEED
    stand_e = stand_amt * stand_amt * (3 - 2 * stand_amt)
    rider_dip = 3.0 * (fork_c + shock_c)

    # ------------------------------------------------------------ draw
    style = MAPS[current_map]

    screen.blit(sky_surfaces[current_map], (0, 0))

    if current_map == 0:
        draw_clouds((255, 140, 125), (255, 170, 140), 0.04)
        draw_mountains(HEIGHT - 235, (120, 50, 105), 0.05, 1)
        draw_mountains(HEIGHT - 185, (75, 32, 85), 0.15, 2)
    else:
        draw_clouds((255, 255, 255), (238, 247, 255), 0.04, limit_y=240)
        draw_waves()
        draw_sailboat()
        draw_sand()
        draw_beach_props()

    draw_road()

    rear_x = bike_x
    rear_y = ground_height(rear_x) - WHEEL_RADIUS
    draw_bike(rear_x, rear_y, tilt, wheel_rot)

    # HUD
    best_distance = best_distances[current_map]
    speed_text = font.render(f"Speed: {int(speed)}", True, style["hud"])
    dist_text = font.render(f"Distance: {int(distance)}m", True, style["hud"])
    best_text = font.render(f"Best: {int(best_distance)}m", True, style["hud"])

    screen.blit(speed_text, (20, 20))
    screen.blit(dist_text, (20, 80))
    screen.blit(best_text, (20, 140))

    right_lines = [
        f"Map: {style['name']}  (X)",
        f"Bike: {BIKES[current_bike]['name']}  (T)",
        f"Stand: {'ON' if stand_on else 'OFF'}  (F)",
    ]
    for i, line in enumerate(right_lines):
        t = info.render(line, True, style["hud"])
        screen.blit(t, (WIDTH - t.get_width() - 20, 20 + i * 35))

    controls = info.render(
        "RIGHT = Gas + Wheelie | LEFT = Brake | F = Stand | X = Map | T = Bike",
        True,
        style["hud_bottom"],
    )
    screen.blit(controls, (20, HEIGHT - 50))

    if crashed:

        crash_text = font.render(
            "CRASHED! Press R to Restart",
            True,
            RED,
        )

        screen.blit(
            crash_text,
            (
                WIDTH // 2 - crash_text.get_width() // 2,
                120,
            ),
        )

    pygame.display.flip()

pygame.quit()