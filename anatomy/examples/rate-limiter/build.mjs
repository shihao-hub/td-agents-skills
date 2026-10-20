import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "../../kit/iso-kit.mjs";
import { kitScript } from "../../scripts/inline-kit.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const theme = process.argv.includes("--light") ? "light" : "dark";

const WIDTH = 680;
const HEIGHT = 440;

// Coordinate layout
const PLATE = { x: -140, y: -75, w: 280, d: 150, r: 8 };
const PLATE_H = 12;
const FOOT_H = 5;

// Support pillars
const POST_L = [-75, -25];
const POST_R = [65, -25];
const POST_H = 125;

// Magazine / Bucket Cylinder (Borosilicate Glass Tube)
const TUBE = [-35, 0];
const TUBE_R_IN = 10;
const TUBE_R_OUT = 12;
const TUBE_BASE_Z = 16;
const TUBE_H = 92;
const TUBE_TOP = TUBE_BASE_Z + TUBE_H;
const MAX_CAPACITY = 10;
const TOKEN_H = 7.5;
const TOKEN_R = 9;

// Escapement / Refill Mechanism (Top Center-Right)
const ESCAPEMENT_BOX = { x: 5, y: -30, w: 34, d: 30, r: 3 };
const ESC_Z = 85;
const ESC_H = 25;
const MOTOR_KNOB = [22, -15];

// Discharge Gate & Solenoid Plunger (Lower Front of Magazine)
const SOLENOID = [-35, 42];
const SOLENOID_Z = 0;
const SOLENOID_H = 16;

// Dual Dial Gauge (Right Pillar Arm)
const DIAL_MAIN = [75, 10]; // Token count dial
const DIAL_MAIN_R = 21;
const DIAL_MAIN_Z = 75;
const DIAL_MAIN_H = 8;

const DIAL_SUB = [75, 10]; // Rate meter dial
const DIAL_SUB_R = 15;
const DIAL_SUB_Z = 30;
const DIAL_SUB_H = 7;

// Projection
const P = k.fitProjection(
  [
    ...k.boxCorners(PLATE, -PLATE_H - FOOT_H, 0),
    [POST_L[0], POST_L[1], POST_H + 5],
    [POST_R[0], POST_R[1], POST_H + 5],
    [TUBE[0], TUBE[1], TUBE_TOP + 15],
    [DIAL_MAIN[0] + DIAL_MAIN_R + 5, DIAL_MAIN[1], DIAL_MAIN_Z + DIAL_MAIN_H],
  ],
  WIDTH,
  HEIGHT,
  { pad: 30, azimuth: 42, elevation: 30 }
);

const at = (point) => k.iso(point, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const depth = (x, y, z = 0) => k.depthOf([x, y, z], P);
const byDepth = (points) => [...points].sort((a, b) => depth(...a) - depth(...b));

// 1. Base Plate & Feet
function plate() {
  const out = [`<path class="iso-halo" d="${k.haloOf(PLATE, -PLATE_H - FOOT_H, PLATE_H, P)}"/>`];
  
  // 4 Stepped Feet
  for (const [x, y] of byDepth(k.corners(PLATE, 22))) {
    out.push(S(k.cylinder(x, y, 7.5, -PLATE_H - FOOT_H, 1.8, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 5.8, -PLATE_H - FOOT_H + 1.8, FOOT_H - 1.8, P, 28), { tone: "mid" }));
  }

  // Base Slab
  out.push(S(k.slabOf(PLATE, -PLATE_H, PLATE_H, P, 8, 1.6), { tone: "mid" }));
  // Perimeter groove
  out.push(L(k.planOutline(k.insetPlan(PLATE, 5), 0, P), { tone: "lo" }));

  // Corner Screws
  const screws = k.corners(PLATE, 11);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));

  // Front Ruler Scale Strip
  const strip = { x: -125, y: PLATE.y + PLATE.d - 14, w: 160, d: 7, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const ticks = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 4, 5, strip.y + 0.8, 0.6, [1.8, 3.4], P);
  out.push(L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" }));

  // Brass Nameplate
  const nameplate = { x: 45, y: PLATE.y + PLATE.d - 16, w: 85, d: 11, r: 1.5 };
  out.push(S(k.slabOf(nameplate, 0, 0.8, P, 3), { tone: "mid", crease: "none" }));
  out.push(k.faceTextSvg(k.topMatrix([nameplate.x + 6, nameplate.y + 7.5], 0.8, P, "x"), "RATE LIMITER · ESCAPEMENT GOVERNOR", { size: 2.8, tone: "lo" }));
  out.push(D([at([nameplate.x + 3, nameplate.y + 5.5, 0.8]), at([nameplate.x + nameplate.w - 3, nameplate.y + 5.5, 0.8])], { size: 0.45 }));

  return out.join("");
}

// 2. Pillars & Crosshead Frame
function structure() {
  const out = [];

  // Left & Right Pillars
  for (const [x, y] of [POST_L, POST_R]) {
    out.push(S(k.cylinder(x, y, 9, 0, 3.5, P, 28), { tone: "mid" }));
    out.push(L(k.ring(x, y, 7.2, 3.5, P, 20), { tone: "lo" }));
    const bolts = Array.from({ length: 4 }, (_, i) => {
      const a = (i * Math.PI) / 2 + Math.PI / 4;
      return at([x + Math.cos(a) * 6.5, y + Math.sin(a) * 6.5, 3.5]);
    });
    out.push(D(bolts, { size: 0.45 }));
    out.push(S(k.cylinder(x, y, 4.5, 3.5, POST_H - 3.5, P, 28), { tone: "mid", crease: "none" }));
    out.push(L([35, 65, 95].map((z) => k.sideArc(x, y, 4.5, z, P, 20)).join(""), { tone: "faint" }));
    out.push(S(k.cylinder(x, y, 5.5, POST_H, 4, P, 28), { tone: "hi" }));
  }

  // Crosshead tie bar between pillars at Z = 110
  const bar = { x: POST_L[0] + 4, y: -27.5, w: POST_R[0] - POST_L[0] - 8, d: 5, r: 1.2 };
  out.push(S(k.slabOf(bar, 108, 4, P, 3, 0.5), { tone: "mid" }));
  out.push(D([at([bar.x + 6, -25, 112]), at([bar.x + bar.w - 6, -25, 112])], { size: 0.45 }));

  // Clamps holding the tube
  const tubeClamp = { x: TUBE[0] - 15, y: -16, w: 30, d: 14, r: 2 };
  out.push(S(k.slabOf(tubeClamp, 70, 5, P, 3, 0.5), { tone: "mid" }));
  out.push(L(k.ring(TUBE[0], 0, TUBE_R_OUT + 0.4, 75, P, 24), { tone: "lo" }));

  return out.join("");
}

// 3. Magazine / Bucket Assembly (Glass Tube, Manifold & Overflow)
function magazine() {
  const out = [];
  const [tx, ty] = TUBE;

  // Base Manifold Block
  const manifold = { x: tx - 18, y: ty - 18, w: 36, d: 36, r: 3 };
  out.push(S(k.slabOf(manifold, 0, TUBE_BASE_Z, P, 4, 0.8), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(manifold, 2.5), TUBE_BASE_Z, P, 4), { tone: "faint" }));
  
  const manifoldScrews = k.corners(manifold, 4.5);
  out.push(D(manifoldScrews.map(([x, y]) => at([x, y, TUBE_BASE_Z])), { size: 0.4 }));

  // Lower Collar Socket
  out.push(S(k.cylinder(tx, ty, TUBE_R_OUT + 2, TUBE_BASE_Z, 3, P, 36), { tone: "hi" }));

  // Top Collar & Intake Funnel with knurl ring bounds
  out.push(S(k.cylinder(tx, ty, TUBE_R_OUT + 2.5, TUBE_TOP - 2, 4, P, 36), { tone: "mid" }));
  out.push(S(k.cylinder(tx, ty, TUBE_R_OUT + 5, TUBE_TOP + 2, 6, P, 36, 0.8), { tone: "hi" }));
  out.push(L(k.ring(tx, ty, TUBE_R_OUT + 5, TUBE_TOP + 3, P, 36), { tone: "lo" }));
  out.push(L(k.ring(tx, ty, TUBE_R_OUT + 5, TUBE_TOP + 7, P, 36), { tone: "lo" }));
  out.push(L(k.knurl(tx, ty, TUBE_R_OUT + 5, TUBE_TOP + 3, TUBE_TOP + 7, 36, P), { tone: "lo" }));

  // Top Overflow Weir & Pipe (弯曲的溢流管 - 桶满溢出丢弃)
  const pipeStart = [tx - TUBE_R_OUT - 1, ty, TUBE_TOP - 6];
  const pipeMid = [tx - 38, ty - 8, TUBE_TOP - 16];
  const pipeEnd = [tx - 44, ty + 15, 14];
  out.push(k.wireSvg(at(pipeStart), at(pipeEnd), {
    via: [at(pipeMid), at([tx - 44, ty - 2, 45])],
    tone: "mid",
    size: 2.2,
  }));
  // Overflow collection cup
  out.push(S(k.cylinder(tx - 44, ty + 15, 6.5, 0, 14, P, 24, 0.6), { tone: "lo" }));
  out.push(k.faceTextSvg(k.sideMatrix([tx - 44, ty + 22], 10, P, "left"), "OVERFLOW", { size: 2.2, tone: "lo", anchor: "middle" }));

  // Outer Borosilicate Glass Cylinder
  out.push(S(k.cylinder(tx, ty, TUBE_R_OUT, TUBE_BASE_Z + 3, TUBE_H - 5, P, 48), { tone: "lo", className: "tube-glass" }));

  // Graduated Etched Ticks on the Glass (0 to 10 marks)
  for (let i = 1; i <= MAX_CAPACITY; i++) {
    const gz = TUBE_BASE_Z + 3 + i * (TOKEN_H + 0.8);
    out.push(L(k.sideArc(tx, ty, TUBE_R_OUT, gz, P, 24), { tone: i % 5 === 0 ? "hi" : "mid" }));
  }

  return out.join("");
}

// 4. Escapement & Clockwork Refill Station
function escapement() {
  const out = [];

  // Escapement Gear Box
  out.push(S(k.slabOf(ESCAPEMENT_BOX, ESC_Z, ESC_H, P, 4, 0.8), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(ESCAPEMENT_BOX, 2.5), ESC_Z + ESC_H, P, 3), { tone: "faint" }));

  // Refill Rate Micrometer Knob (on top of box)
  const [kx, ky] = MOTOR_KNOB;
  const kz0 = ESC_Z + ESC_H;
  out.push(S(k.cylinder(kx, ky, 8.5, kz0, 6, P, 32), { tone: "hi" }));
  out.push(L(k.ring(kx, ky, 8.5, kz0 + 0.8, P, 32), { tone: "lo" }));
  out.push(L(k.ring(kx, ky, 8.5, kz0 + 5.2, P, 32), { tone: "lo" }));
  out.push(L(k.knurl(kx, ky, 8.5, kz0 + 0.8, kz0 + 5.2, 36, P), { tone: "lo" }));
  out.push(L(k.ring(kx, ky, 5.5, kz0 + 6, P, 24), { tone: "mid" }));
  out.push(D([at([kx, ky, kz0 + 6])], { size: 0.5, tone: "hi" }));

  // Escapement Feed Arm
  const armStart = [ESCAPEMENT_BOX.x, ESCAPEMENT_BOX.y + 12, ESC_Z + 12];
  const armEnd = [TUBE[0] + TUBE_R_OUT + 2, TUBE[1], TUBE_TOP + 4];
  out.push(S(k.slabOf({ x: armEnd[0], y: armEnd[1] - 2, w: armStart[0] - armEnd[0], d: 4, r: 1 }, ESC_Z + 10, 3, P, 2), { tone: "hi" }));
  out.push(D([at([armStart[0], armStart[1], ESC_Z + 13]), at([armEnd[0] + 3, armEnd[1], ESC_Z + 13])], { size: 0.45 }));

  // Star Ratchet Wheel on front face of gearbox
  const ratchetCenter = [ESCAPEMENT_BOX.x + 10, ESCAPEMENT_BOX.y + ESCAPEMENT_BOX.d, ESC_Z + 8];
  out.push(L(k.ring(ratchetCenter[0], ratchetCenter[1], 4.5, ratchetCenter[2], P, 16), { tone: "hi" }));
  out.push(D([at(ratchetCenter)], { size: 0.5, tone: "lit" }));

  return out.join("");
}

// 5. Request Actuator Plunger & Gate Mechanism (Solenoid)
function actuator() {
  const out = [];
  const [sx, sy] = SOLENOID;

  // Plunger Base Mount
  const sbase = { x: sx - 12, y: sy - 12, w: 24, d: 24, r: 2.5 };
  out.push(S(k.slabOf(sbase, 0, 4, P, 3, 0.5), { tone: "mid" }));
  
  // Solenoid Cylinder Housing
  out.push(S(k.cylinder(sx, sy, 8, 4, SOLENOID_H, P, 32), { tone: "mid" }));
  out.push(L([8, 12, 16].map((z) => k.sideArc(sx, sy, 8, z, P, 20)).join(""), { tone: "faint" }));

  // Push Button Plunger (Moves when pressed)
  const pz0 = 4 + SOLENOID_H;
  out.push(`<g data-part="plunger">`);
  out.push(S(k.cylinder(sx, sy, 5.5, pz0, 6, P, 28), { tone: "hi", lit: true }));
  out.push(L(k.ring(sx, sy, 5.5, pz0 + 1, P, 24), { tone: "lo" }));
  out.push(L(k.ring(sx, sy, 5.5, pz0 + 5, P, 24), { tone: "lo" }));
  out.push(L(k.knurl(sx, sy, 5.5, pz0 + 1, pz0 + 5, 24, P), { tone: "lo" }));
  out.push(D([at([sx, sy, pz0 + 6])], { size: 0.5, tone: "lit" }));
  out.push(`</g>`);

  // Solenoid Connection Linkage to Magazine Base
  const link = { x: sx - 2, y: TUBE[1] + 16, w: 4, d: sy - 12 - (TUBE[1] + 16), r: 1 };
  out.push(S(k.slabOf(link, 5, 3, P, 2), { tone: "hi" }));

  // Flow Output Chute
  const chute = { x: TUBE[0] + 6, y: TUBE[1] + 10, w: 50, d: 8, r: 1.5 };
  out.push(S(k.slabOf(chute, 3, 3, P, 3, 0.4), { tone: "mid" }));
  out.push(L(k.lineOnTop([chute.x, chute.y + 4], [chute.x + chute.w, chute.y + 4], 6, P), { tone: "faint" }));

  // Pass Indicator Gate Jewel
  const jewel = [chute.x + chute.w - 3, chute.y + 4, 6];
  out.push(S(k.cylinder(jewel[0], jewel[1], 2.8, 6, 2, P, 16), { tone: "hi", className: "jewel-bezel" }));
  out.push(`<circle class="iso-jewel" data-part="jewel" cx="${at(jewel)[0].toFixed(1)}" cy="${at(jewel)[1].toFixed(1)}" r="2.2"/>`);

  return out.join("");
}

// 6. Dual Dial Gauges (Tokens Gauge & Flow Rate Gauge)
function dials() {
  const out = [];

  // Gauge Mount Arm off Right Pillar
  const arm = { x: POST_R[0] - 2, y: POST_R[1] + 4, w: DIAL_MAIN[0] - POST_R[0] + 6, d: 7, r: 1.5 };
  out.push(S(k.slabOf(arm, DIAL_MAIN_Z + 1, 4, P, 3), { tone: "mid" }));
  out.push(S(k.slabOf(arm, DIAL_SUB_Z + 1, 4, P, 3), { tone: "mid" }));

  // Upper Dial: Token / Bucket Gauge (0 - 10)
  const [mx, my] = DIAL_MAIN;
  out.push(S(k.cylinder(mx, my, DIAL_MAIN_R, DIAL_MAIN_Z, DIAL_MAIN_H, P, 56, 0.8), { tone: "hi" }));
  out.push(L(k.ring(mx, my, DIAL_MAIN_R, DIAL_MAIN_Z + 4, P, 48), { tone: "lo" }));
  out.push(L(k.ring(mx, my, DIAL_MAIN_R, DIAL_MAIN_Z + DIAL_MAIN_H - 1, P, 48), { tone: "lo" }));
  out.push(L(k.knurl(mx, my, DIAL_MAIN_R, DIAL_MAIN_Z + 4, DIAL_MAIN_Z + DIAL_MAIN_H - 1, 64, P), { tone: "lo" }));
  out.push(L(k.ring(mx, my, DIAL_MAIN_R - 2.2, DIAL_MAIN_Z + DIAL_MAIN_H, P, 48), { tone: "lo" }));
  
  // Radial ticks rooted on ring radius DIAL_MAIN_R - 2.2
  const mainTicks = k.radialTicks(mx, my, DIAL_MAIN_R - 2.2, 10, 2, DIAL_MAIN_Z + DIAL_MAIN_H, [1.4, 2.8], P, -Math.PI * 0.75, Math.PI * 1.5);
  out.push(L(mainTicks.minor, { tone: "lo" }), L(mainTicks.major, { tone: "hi" }));
  out.push(L(k.ring(mx, my, 1.8, DIAL_MAIN_Z + DIAL_MAIN_H, P, 16), { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([mx, my + 8], DIAL_MAIN_Z + DIAL_MAIN_H, P, "x"), "TOKENS / 10", { size: 2.3, tone: "lo", anchor: "middle" }));

  // Lower Dial: Throughput Rate Gauge (Req/s)
  const [sx, sy] = DIAL_SUB;
  out.push(S(k.cylinder(sx, sy, DIAL_SUB_R, DIAL_SUB_Z, DIAL_SUB_H, P, 48, 0.6), { tone: "mid" }));
  out.push(L(k.ring(sx, sy, DIAL_SUB_R, DIAL_SUB_Z + 3, P, 36), { tone: "lo" }));
  out.push(L(k.ring(sx, sy, DIAL_SUB_R, DIAL_SUB_Z + DIAL_SUB_H - 1, P, 36), { tone: "lo" }));
  out.push(L(k.knurl(sx, sy, DIAL_SUB_R, DIAL_SUB_Z + 3, DIAL_SUB_Z + DIAL_SUB_H - 1, 48, P), { tone: "lo" }));
  out.push(L(k.ring(sx, sy, DIAL_SUB_R - 1.8, DIAL_SUB_Z + DIAL_SUB_H, P, 40), { tone: "lo" }));
  
  // Radial ticks rooted on ring radius DIAL_SUB_R - 1.8
  const subTicks = k.radialTicks(sx, sy, DIAL_SUB_R - 1.8, 8, 2, DIAL_SUB_Z + DIAL_SUB_H, [1.1, 2.2], P, -Math.PI * 0.75, Math.PI * 1.5);
  out.push(L(subTicks.minor, { tone: "lo" }), L(subTicks.major, { tone: "mid" }));
  out.push(L(k.ring(sx, sy, 1.5, DIAL_SUB_Z + DIAL_SUB_H, P, 16), { tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([sx, sy + 6], DIAL_SUB_Z + DIAL_SUB_H, P, "x"), "REQ / SEC", { size: 1.9, tone: "lo", anchor: "middle" }));

  return out.join("");
}

// Needles calculation
const needleOnDial = (cx, cy, radius, z, angleRad) => {
  const innerR = 2.4;
  const outerR = radius - 3.5;
  const p0 = [cx - Math.sin(angleRad) * innerR, cy + Math.cos(angleRad) * innerR];
  const p1 = [cx + Math.sin(angleRad) * outerR, cy - Math.cos(angleRad) * outerR];
  return k.lineOnTop(p0, p1, z + 0.2, P);
};

// Generate dynamic token slots
function tokenSlots() {
  const [tx, ty] = TUBE;
  const out = [];
  for (let i = 0; i < MAX_CAPACITY; i++) {
    const tz = TUBE_BASE_Z + 4 + i * (TOKEN_H + 0.8);
    out.push(`<g data-token="${i}" class="iso-token" style="transition:opacity .15s ease">`);
    out.push(S(k.cylinder(tx, ty, TOKEN_R, tz, TOKEN_H, P, 32, 0.4), { tone: "hi", lit: true }));
    out.push(L(k.sideArc(tx, ty, TOKEN_R, tz + TOKEN_H / 2, P, 24), { tone: "lo" }));
    out.push(`</g>`);
  }
  return out.join("");
}

// Assembled SVG
const initialTokens = 6;
const mainAngle = -Math.PI * 0.75 + (initialTokens / MAX_CAPACITY) * Math.PI * 1.5;
const subAngle = -Math.PI * 0.75 + 0.3 * Math.PI * 1.5;

const svg = k.figureSvg({
  width: WIDTH,
  height: HEIGHT,
  label: "A dual-mode precision rate limiting governor apparatus mounted on a granite surface plate.",
  body: [
    plate(),
    structure(),
    magazine(),
    tokenSlots(),
    escapement(),
    actuator(),
    dials(),
    `<path data-part="needle-tokens" class="iso-line iso-needle" data-tone="lit" data-free="start" d="${needleOnDial(DIAL_MAIN[0], DIAL_MAIN[1], DIAL_MAIN_R, DIAL_MAIN_Z + DIAL_MAIN_H, mainAngle)}" style="stroke-width:1.2"/>`,
    `<path data-part="needle-rate" class="iso-line iso-needle" data-tone="lit" data-free="start" d="${needleOnDial(DIAL_SUB[0], DIAL_SUB[1], DIAL_SUB_R, DIAL_SUB_Z + DIAL_SUB_H, subAngle)}" style="stroke-width:1.0"/>`,
  ],
});

// Interactive Client-Side Script
const live = `
const P = ${JSON.stringify(P)};
const DIAL_MAIN = ${JSON.stringify(DIAL_MAIN)};
const DIAL_MAIN_R = ${DIAL_MAIN_R}, DIAL_MAIN_Z = ${DIAL_MAIN_Z}, DIAL_MAIN_H = ${DIAL_MAIN_H};
const DIAL_SUB = ${JSON.stringify(DIAL_SUB)};
const DIAL_SUB_R = ${DIAL_SUB_R}, DIAL_SUB_Z = ${DIAL_SUB_Z}, DIAL_SUB_H = ${DIAL_SUB_H};
const MAX_CAPACITY = ${MAX_CAPACITY};

const stage = document.querySelector(".iso-stage");
const svg = stage.querySelector("svg");
const needleTokens = svg.querySelector('[data-part="needle-tokens"]');
const needleRate = svg.querySelector('[data-part="needle-rate"]');
const plunger = svg.querySelector('[data-part="plunger"]');
const jewel = svg.querySelector('[data-part="jewel"]');
const tokenElements = Array.from(svg.querySelectorAll('[data-token]'));
const readout = document.querySelector("[data-readout]");

const needleOnDial = ${needleOnDial.toString().replace("k.lineOnTop", "lineOnTop")};

// Simulation State
let mode = "token-bucket";
let tokens = 6.0;
let refillRate = 2.0;
let leakyQueue = 0.0;
let fixedWindowCount = 0;
let windowStart = performance.now();
const WINDOW_DURATION = 5000;
let slidingLogs = [];

let totalReq = 0;
let passedReq = 0;
let throttledReq = 0;

let lastTime = performance.now();
let plungerPressed = 0;
let jewelFlash = 0;
let dialTokensTarget = tokens;
let dialTokensCurrent = tokens;
let dialRateCurrent = 0;

function sendRequest(isBurst = false) {
  const now = performance.now();
  totalReq++;
  let passed = false;

  if (mode === "token-bucket") {
    if (tokens >= 1.0) {
      tokens -= 1.0;
      passed = true;
    }
  } else if (mode === "leaky-bucket") {
    if (leakyQueue + 1.0 <= MAX_CAPACITY) {
      leakyQueue += 1.0;
      passed = true;
    }
  } else if (mode === "fixed-window") {
    if (now - windowStart >= WINDOW_DURATION) {
      windowStart = now;
      fixedWindowCount = 0;
    }
    if (fixedWindowCount < MAX_CAPACITY) {
      fixedWindowCount++;
      passed = true;
    }
  } else if (mode === "sliding-window") {
    slidingLogs = slidingLogs.filter(t => now - t < WINDOW_DURATION);
    if (slidingLogs.length < MAX_CAPACITY) {
      slidingLogs.push(now);
      passed = true;
    }
  }

  if (passed) {
    passedReq++;
    jewelFlash = 1.0;
  } else {
    throttledReq++;
    jewelFlash = -1.0;
  }

  plungerPressed = 1.0;
  updateUI();
}

function sendBurst(count = 6) {
  for (let i = 0; i < count; i++) {
    setTimeout(() => sendRequest(true), i * 35);
  }
}

function updateSimulation(dt) {
  const now = performance.now();

  if (mode === "token-bucket") {
    tokens = Math.min(MAX_CAPACITY, tokens + refillRate * dt);
    dialTokensTarget = tokens;
  } else if (mode === "leaky-bucket") {
    leakyQueue = Math.max(0, leakyQueue - refillRate * dt);
    dialTokensTarget = MAX_CAPACITY - leakyQueue;
  } else if (mode === "fixed-window") {
    if (now - windowStart >= WINDOW_DURATION) {
      windowStart = now;
      fixedWindowCount = 0;
    }
    dialTokensTarget = MAX_CAPACITY - fixedWindowCount;
  } else if (mode === "sliding-window") {
    slidingLogs = slidingLogs.filter(t => now - t < WINDOW_DURATION);
    dialTokensTarget = MAX_CAPACITY - slidingLogs.length;
  }

  dialTokensCurrent += (dialTokensTarget - dialTokensCurrent) * (1 - Math.exp(-dt / 0.12));
  
  const targetRate = mode === "leaky-bucket" && leakyQueue > 0 ? refillRate : (passedReq > 0 ? Math.min(5, passedReq / 2) : 0);
  dialRateCurrent += (targetRate - dialRateCurrent) * (1 - Math.exp(-dt / 0.25));

  if (plungerPressed > 0) {
    plungerPressed = Math.max(0, plungerPressed - dt * 6);
  }
  if (Math.abs(jewelFlash) > 0) {
    jewelFlash *= Math.exp(-dt * 4);
    if (Math.abs(jewelFlash) < 0.05) jewelFlash = 0;
  }

  render();
}

function render() {
  const visibleCount = Math.round(dialTokensCurrent);
  tokenElements.forEach((el, index) => {
    el.style.opacity = index < visibleCount ? "1" : "0.08";
  });

  const tokenAngle = -Math.PI * 0.75 + (dialTokensCurrent / MAX_CAPACITY) * Math.PI * 1.5;
  needleTokens.setAttribute("d", needleOnDial(DIAL_MAIN[0], DIAL_MAIN[1], DIAL_MAIN_R, DIAL_MAIN_Z + DIAL_MAIN_H, tokenAngle));

  const rateAngle = -Math.PI * 0.75 + (Math.min(5, dialRateCurrent) / 5) * Math.PI * 1.5;
  needleRate.setAttribute("d", needleOnDial(DIAL_SUB[0], DIAL_SUB[1], DIAL_SUB_R, DIAL_SUB_Z + DIAL_SUB_H, rateAngle));

  const dy = plungerPressed * 3.5;
  plunger.setAttribute("transform", translateAlong(P, [0, 0, -dy]));

  if (jewelFlash > 0.1) {
    jewel.style.fill = "var(--anatomy-green)";
    jewel.style.filter = "drop-shadow(0 0 4px var(--anatomy-green))";
  } else if (jewelFlash < -0.1) {
    jewel.style.fill = "var(--anatomy-red)";
    jewel.style.filter = "drop-shadow(0 0 4px var(--anatomy-red))";
  } else {
    jewel.style.fill = "var(--anatomy-lo)";
    jewel.style.filter = "none";
  }
}

function updateUI() {
  const shortModes = {
    "token-bucket": "令牌桶",
    "leaky-bucket": "漏桶",
    "fixed-window": "固定窗口",
    "sliding-window": "滑动窗口"
  };

  const levelText = mode === "leaky-bucket" ? (leakyQueue.toFixed(1) + "/10 水位") : (tokens.toFixed(1) + "/10 令牌");
  const statusStr = jewelFlash < -0.1 ? "429 阻断" : "200 放行";
  readout.textContent = shortModes[mode] + " · " + levelText + " · " + statusStr;

  // Update detail cards in dashboard
  const descEl = document.getElementById("mode-desc");
  const descs = {
    "token-bucket": "【令牌桶 Token Bucket】恒速投放令牌，桶满溢出。支持瞬间突发（Burst）：桶内有多少令牌就能瞬间消费多少，耗尽后退化为恒速放行。",
    "leaky-bucket": "【漏桶 Leaky Bucket】请求倒入蓄水桶暂存，桶底恒速滴水处理。容量满时溢流丢弃。彻底消弭流量尖峰，输出绝对匀速平滑（Traffic Shaping）。",
    "fixed-window": "【固定窗口计数器】5秒周期内累计限额 10 次。存在临界突发缺陷：在 4.9s 耗尽 10 次后，5.1s 新窗口又获 10 次，瞬时遭遇 20 次双倍冲击！",
    "sliding-window": "【滑动窗口日志/计数器】根据时间戳动态衰减前一窗口请求占比，彻底抹平固定窗口切换时的临界突发悬崖，提供平滑平移保护。"
  };
  if (descEl) descEl.textContent = descs[mode];

  const statTotal = document.getElementById("stat-total");
  const statPass = document.getElementById("stat-pass");
  const statBlock = document.getElementById("stat-block");
  const statPct = document.getElementById("stat-pct");
  if (statTotal) statTotal.textContent = totalReq;
  if (statPass) statPass.textContent = passedReq;
  if (statBlock) statBlock.textContent = throttledReq;
  if (statPct) statPct.textContent = totalReq > 0 ? ((passedReq / totalReq) * 100).toFixed(1) + "%" : "100%";
}

let lastFrame = performance.now();
function loop(now) {
  const dt = Math.min((now - lastFrame) / 1000, 0.1);
  lastFrame = now;
  updateSimulation(dt);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

stage.addEventListener("click", () => sendRequest());
window.addEventListener("keydown", (e) => {
  if (e.code === "Space") {
    e.preventDefault();
    sendRequest();
  } else if (e.key === "b" || e.key === "B") {
    sendBurst(6);
  } else if (e.key === "1") {
    setMode("token-bucket");
  } else if (e.key === "2") {
    setMode("leaky-bucket");
  } else if (e.key === "3") {
    setMode("fixed-window");
  } else if (e.key === "4") {
    setMode("sliding-window");
  }
});

window.setMode = (m) => {
  mode = m;
  tokens = 6.0;
  leakyQueue = 0.0;
  fixedWindowCount = 0;
  slidingLogs = [];
  document.querySelectorAll("[data-mode-btn]").forEach(b => {
    b.classList.toggle("active", b.dataset.modeBtn === m);
  });
  updateUI();
};

window.triggerBurst = () => sendBurst(6);
window.triggerSingle = () => sendRequest();
window.setRefill = (val) => {
  refillRate = parseFloat(val);
  document.getElementById("rate-label").textContent = refillRate.toFixed(1) + " /s";
};

updateUI();
`;

// Additional Controls & Interactive Dashboard
const DASHBOARD_HTML = `
<div class="rl-dashboard">
  <div class="rl-toolbar">
    <div class="rl-btn-group">
      <button class="rl-btn active" data-mode-btn="token-bucket" onclick="setMode('token-bucket')">1. 令牌桶 (Token Bucket)</button>
      <button class="rl-btn" data-mode-btn="leaky-bucket" onclick="setMode('leaky-bucket')">2. 漏桶 (Leaky Bucket)</button>
      <button class="rl-btn" data-mode-btn="fixed-window" onclick="setMode('fixed-window')">3. 固定窗口 (Fixed Window)</button>
      <button class="rl-btn" data-mode-btn="sliding-window" onclick="setMode('sliding-window')">4. 滑动窗口 (Sliding Window)</button>
    </div>
    <div class="rl-actions">
      <button class="rl-btn rl-action-btn" onclick="triggerSingle()">⚡ 单次请求 (Space)</button>
      <button class="rl-btn rl-action-btn rl-burst" onclick="triggerBurst()">💥 瞬发突发 6 次 (B)</button>
      <div class="rl-slider-wrap">
        <label>补给/漏出速率 r:</label>
        <input type="range" min="0.5" max="5.0" step="0.5" value="2.0" oninput="setRefill(this.value)">
        <span id="rate-label">2.0 /s</span>
      </div>
    </div>
  </div>

  <div id="mode-desc" class="rl-desc">
    【令牌桶 Token Bucket】恒速投放令牌，桶满溢出。支持瞬间突发（Burst）：桶内有多少令牌就能瞬间消费多少，耗尽后退化为恒速放行。
  </div>

  <div class="rl-stats">
    <div class="rl-stat"><span class="rl-label">总请求数</span><span id="stat-total" class="rl-val">0</span></div>
    <div class="rl-stat"><span class="rl-label">放行成功 (200)</span><span id="stat-pass" class="rl-val pass">0</span></div>
    <div class="rl-stat"><span class="rl-label">限流阻断 (429)</span><span id="stat-block" class="rl-val block">0</span></div>
    <div class="rl-stat"><span class="rl-label">放行成功率</span><span id="stat-pct" class="rl-val">100%</span></div>
  </div>
</div>
`;

const CSS = `
.tube-glass { opacity: 0.85; stroke-dasharray: 2 1; }
.iso-token { transition: opacity .18s ease; }
.iso-needle { transition: d .05s ease; }
.iso-jewel { transition: fill .1s, filter .1s; }
.iso-stage { cursor: pointer; touch-action: manipulation; }
.rl-dashboard { margin-top: 24px; display: flex; flex-direction: column; gap: 14px; }
.rl-toolbar { display: flex; flex-direction: column; gap: 10px; }
.rl-btn-group { display: flex; flex-wrap: wrap; gap: 8px; }
.rl-btn {
  background: var(--anatomy-card);
  color: var(--anatomy-text);
  border: 1px solid var(--anatomy-lo);
  border-radius: 4px;
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: all .15s;
}
.rl-btn:hover { border-color: var(--anatomy-mid); color: var(--anatomy-strong); }
.rl-btn.active { border-color: var(--anatomy-strong); color: var(--anatomy-strong); background: var(--anatomy-face); font-weight: 600; }
.rl-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.rl-action-btn { background: var(--anatomy-face); border-color: var(--anatomy-mid); }
.rl-burst { color: var(--anatomy-red); border-color: var(--anatomy-red); font-weight: 600; }
.rl-slider-wrap { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--anatomy-text); margin-left: auto; }
.rl-slider-wrap input { width: 100px; accent-color: var(--anatomy-strong); }
.rl-desc {
  padding: 12px 14px;
  background: var(--anatomy-card);
  border: 1px solid var(--anatomy-lo);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--anatomy-text);
}
.rl-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.rl-stat {
  padding: 10px 12px;
  background: var(--anatomy-card);
  border: 1px solid var(--anatomy-lo);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rl-label { font-size: 11px; color: var(--anatomy-muted); }
.rl-val { font-size: 18px; font-weight: 600; font-family: var(--anatomy-mono); color: var(--anatomy-strong); }
.rl-val.pass { color: var(--anatomy-green); }
.rl-val.block { color: var(--anatomy-red); }
`;

const plateBlock = k.plateHtml({
  fig: "Fig 1",
  title: "Precision Rate Limiting Governor",
  hint: "Click or Space to send · B for burst",
  readout: "令牌桶 · 6.0/10 令牌 · 200 放行",
  keys: [
    { mark: "lit", label: "Glass magazine: steel tokens / fluid reservoir (Capacity = 10)" },
    { mark: "raised", label: "Clockwork escapement & micrometer knob: constant refill rate r" },
    { mark: "flat", label: "Gating plunger & jewel sensor: green=pass, red=throttled" },
  ],
  caption:
    "台式精密流量节流与令牌棘轮定标仪 (The Escapement Rate Limiter Rig)。左侧高硼硅立柱容纳 10 枚金属令牌，顶部发条棘轮以恒定速率 r 补给令牌（满则由旁路泄出）；前端电磁推杆响应请求，消耗令牌放行（绿灯），令牌空则卡死硬限位阻断（红灯）。切换漏桶模式则变为恒速泄流，窗口模式则展现临界突发与平滑消除对比。",
  body: `<div class="iso-stage" tabindex="0" role="slider" aria-label="Rate Limiter Governor: click or press Space to send requests">${svg}</div>`,
});

const html = k.pageHtml({
  title: "Rate Limiting Algorithms · Anatomy",
  theme,
  body: `${plateBlock}${DASHBOARD_HTML}`,
  script: kitScript() + live,
  width: 720,
});

const finalHtml = html.replace("</style>", `${CSS}</style>`);

writeFileSync(join(HERE, theme === "light" ? "rate-limiter-light.html" : "rate-limiter.html"), finalHtml);
console.log("wrote", theme === "light" ? "rate-limiter-light.html" : "rate-limiter.html");
