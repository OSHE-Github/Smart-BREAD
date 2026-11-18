import os, cv2, ast, time, json
import numpy as np
import onnxruntime as ort

providers = ("WebGpuExecutionProvider", "CPUExecutionProvider")
thresh = 72.0
totalTime = 0.0
sesIndex = -1

sessions = list()
session_names = list()
model_keys = list()
saved_profiles = dict()
flag_map = dict()
PROFILE_PATH = "model_profiles.json"

BELT_X_MIN = 0.24
BELT_X_MAX = 0.76
LINE_Y_NORM = 0.308
prev_tracked = list()


def resolve_branch_name(names_meta, b_idx, cid):
    if isinstance(names_meta, list):
        entry = names_meta[b_idx] if b_idx < len(names_meta) else f"Class_{b_idx}"
    elif isinstance(names_meta, dict):
        entry = names_meta.get(b_idx, names_meta.get(cid, f"Class_{b_idx}"))
    else:
        return str(names_meta)
    if isinstance(entry, dict):
        val = entry.get(cid, next(iter(entry.values())))
        return val.get("name", next(iter(val.values()))) if isinstance(val, dict) else str(val)
    return str(entry)

def compute_box_signature(img_bgr, box):
    rx1, ry1, rx2, ry2 = box
    h_img, w_img = img_bgr.shape[:2]
    w = max(1, rx2 - rx1)
    h = max(1, ry2 - ry1)
    norm_area = (w * h) / float(w_img * h_img)
    crop = img_bgr[ry1 + int(h * 0.15):ry2 - int(h * 0.15), rx1 + int(w * 0.15):rx2 - int(w * 0.15)]
    if crop.size == 0:
        crop = img_bgr[ry1:ry2, rx1:rx2]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist((hsv,), (0, 1), None, (16, 16), (0, 180, 0, 256))
    cv2.normalize(hist, hist, 1.0, 0.0, cv2.NORM_L1)
    edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 60, 150)
    return {
        "hist": hist.flatten().tolist(),
        "norm_area": float(norm_area),
        "mean_sat": float(np.mean(hsv[:, :, 1])) / 255.0,
        "mean_val": float(np.mean(hsv[:, :, 2])) / 255.0,
        "edge_density": float(np.mean(edges)) / 255.0,
    }


def compare_signatures(sig_a, sig_b):
    if sig_a is None or sig_b is None:
        return 1.0
    ha = np.array(sig_a.get("hist"), dtype=np.float32)
    hb = np.array(sig_b.get("hist"), dtype=np.float32)
    c_sim = max(0.0, 1.0 - cv2.compareHist(ha, hb, cv2.HISTCMP_BHATTACHARYYA))
    sv_sim = max(0.0, 1.0 - (abs(sig_a.get("mean_sat") - sig_b.get("mean_sat")) * 1.5 + abs(sig_a.get("mean_val") - sig_b.get("mean_val")) * 0.6))
    a_ratio = min(max(1e-6, sig_a.get("norm_area")), max(1e-6, sig_b.get("norm_area"))) / max(max(1e-6, sig_a.get("norm_area")), max(1e-6, sig_b.get("norm_area")))
    e_sim = max(0.0, 1.0 - abs(sig_a.get("edge_density") - sig_b.get("edge_density")) * 3.0)
    return max(0.05, min(1.0, 0.30 * c_sim + 0.30 * sv_sim + 0.25 * a_ratio + 0.15 * e_sim))

def box_area(det):
    x1, y1, x2, y2 = det.get("box")
    return (x2 - x1) * (y2 - y1)

def suppress_nested_boxes(dets, contain_thresh=0.60):
    ordered = sorted(dets, key=box_area, reverse=True)
    kept = list()
    for cand in ordered:
        bx1, by1, bx2, by2 = cand.get("box")
        area_c = max(1, (bx2 - bx1) * (by2 - by1))
        nested = False
        for p in kept:
            px1, py1, px2, py2 = p.get("box")
            inter = max(0, min(bx2, px2) - max(bx1, px1)) * max(0, min(by2, py2) - max(by1, py1))
            if (inter / float(area_c)) >= contain_thresh:
                nested = True
                break
        if not nested:
            kept.append(cand)
    return kept

def run_pass(session, canvas, pad_x, pad_y, scale, orig_w, orig_h, names_meta, prefix, ses_idx, img_bgr, rot_deg=0):
    if rot_deg == 90:
        work = cv2.rotate(canvas, cv2.ROTATE_90_CLOCKWISE)
    elif rot_deg == 180:
        work = cv2.rotate(canvas, cv2.ROTATE_180)
    else:
        work = canvas
    rgb = cv2.cvtColor(work, cv2.COLOR_BGR2RGB)
    blob = np.expand_dims(np.transpose(np.ascontiguousarray(rgb, dtype=np.float32) / 255.0, (2, 0, 1)), 0)
    first_input = next(iter(session.get_inputs()))
    objects = session.run(None, {first_input.name: blob})
    cands = list()
    for b_idx, obj in enumerate(objects):
        preds = np.transpose(np.squeeze(obj, axis=0))
        boxes, scores = preds[:, :4], preds[:, 4:]
        cids, confs = np.argmax(scores, axis=1), np.max(scores, axis=1)
        mask = confs > (thresh / 100.0)
        prof_key = f"{prefix}_b{b_idx}"
        ref_sig = saved_profiles.get(prof_key)
        for box, conf, cid in zip(boxes[mask], confs[mask], cids[mask]):
            bx, by, bw, bh = float(box.item(0)), float(box.item(1)), float(box.item(2)), float(box.item(3))
            if rot_deg == 90:
                cx, cy, w, h = by, 640.0 - bx, bh, bw
            elif rot_deg == 180:
                cx, cy, w, h = 640.0 - bx, 640.0 - by, bw, bh
            else:
                cx, cy, w, h = bx, by, bw, bh
            x1, y1, x2, y2 = cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0
            rx1, ry1 = max(0, int((x1 - pad_x) / scale)), max(0, int((y1 - pad_y) / scale))
            rx2, ry2 = min(orig_w, int((x2 - pad_x) / scale)), min(orig_h, int((y2 - pad_y) / scale))
            if rx2 <= rx1 or ry2 <= ry1:
                continue
            cx_norm = ((rx1 + rx2) * 0.5) / float(orig_w)
            if cx_norm < BELT_X_MIN or cx_norm > BELT_X_MAX:
                continue
            raw_score = float(conf)
            live_sig = compute_box_signature(img_bgr, (rx1, ry1, rx2, ry2))
            sim = compare_signatures(live_sig, ref_sig) if ref_sig is not None else 1.0
            fid = flag_map.get((ses_idx, b_idx, int(cid)), b_idx)
            cands.append({
                "box_640": (x1, y1, x2, y2),
                "box": (rx1, ry1, rx2, ry2),
                "confidence": raw_score * sim,
                "raw": raw_score,
                "prof_key": prof_key,
                "sig": live_sig,
                "name": resolve_branch_name(names_meta, b_idx, int(cid)),
                "flag_id": fid,
            })
    return cands

def check_line_crossing(dets, line_y, max_dist=75.0):
    global prev_tracked
    next_tracked = list()
    crossed_flag = -1
    for det in dets:
        rx1, ry1, rx2, ry2 = det.get("box")
        cx, cy = (rx1 + rx2) * 0.5, (ry1 + ry2) * 0.5
        det["center"] = (int(cx), int(cy))
        det["crossed"] = False
        best_prev, best_dist = None, max_dist
        for p in prev_tracked:
            dist = float(np.hypot(cx - p.get("cx"), cy - p.get("cy")))
            if dist < best_dist:
                best_dist, best_prev = dist, p
        triggered = False
        if best_prev is not None:
            prev_y = best_prev.get("cy")
            triggered = best_prev.get("triggered")
            if ((prev_y < line_y <= cy) or (prev_y > line_y >= cy)) and not triggered:
                det["crossed"] = True
                triggered = True
                if crossed_flag == -1:
                    crossed_flag = det.get("flag_id")
        next_tracked.append({"cx": cx, "cy": cy, "flag_id": det.get("flag_id"), "triggered": triggered})
    prev_tracked = next_tracked
    return crossed_flag

def findobj(img):
    global totalTime, thresh, sessions, sesIndex, saved_profiles
    outimg = img.copy()
    orig_h, orig_w = img.shape[:2]
    line_y = int(orig_h * LINE_Y_NORM)
    cv2.line(outimg, (int(orig_w * BELT_X_MIN), line_y), (int(orig_w * BELT_X_MAX), line_y), (0, 255, 255), 2)
    scale = min(640 / orig_w, 640 / orig_h)
    nw, nh = int(orig_w * scale), int(orig_h * scale)
    canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
    pad_x, pad_y = (640 - nw) // 2, (640 - nh) // 2
    canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = cv2.resize(img, (nw, nh))
    sesIndex = (sesIndex + 1) % len(sessions)
    session = sessions[sesIndex]
    names_meta = session_names[sesIndex]
    prefix = model_keys[sesIndex]
    t0 = time.perf_counter()
    cands = run_pass(session, canvas, pad_x, pad_y, scale, orig_w, orig_h, names_meta, prefix, sesIndex, img, 0)
    if not cands:
        cands = run_pass(session, canvas, pad_x, pad_y, scale, orig_w, orig_h, names_meta, prefix, sesIndex, img, 90)
    if not cands:
        cands = run_pass(session, canvas, pad_x, pad_y, scale, orig_w, orig_h, names_meta, prefix, sesIndex, img, 180)
    totalTime += time.perf_counter() - t0
    final_dets = list()
    crossed_flag = -1
    if cands:
        if len({c.get("prof_key") for c in cands}) == 1:
            top_c = max(cands, key=lambda c: c.get("raw"))
            if top_c.get("prof_key") not in saved_profiles and top_c.get("raw") > 0.80 and top_c.get("sig") is not None:
                saved_profiles[top_c.get("prof_key")] = top_c.get("sig")
                with open(PROFILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(saved_profiles, f)
        indices = cv2.dnn.NMSBoxes(tuple(c.get("box_640") for c in cands), tuple(c.get("confidence") for c in cands), 0.35, 0.45)
        if len(indices) > 0:
            nms_dets = list(
                {"box": cands[i].get("box"), "confidence": cands[i].get("confidence"), "name": cands[i].get("name"), "flag_id": cands[i].get("flag_id")}
                for i in indices.flatten()
            )
            final_dets = suppress_nested_boxes(nms_dets, 0.60)
            crossed_flag = check_line_crossing(final_dets, line_y)
            bt = max(4, int(orig_h / 100))
            ft = max(4, int(bt / 3))
            fs = max(1.2, orig_h / 800)
            for det in final_dets:
                rx1, ry1, rx2, ry2 = det.get("box")
                color = (0, 140, 255) if det.get("crossed") else (0, 255, 0)
                tag = f" [FLAG {det.get('flag_id')}]" if det.get("crossed") else ""
                cv2.rectangle(outimg, (rx1, ry1), (rx2, ry2), color, bt)
                cv2.putText(outimg, f"{det.get('name')}: {det.get('confidence')*100:.1f}%{tag}", (rx1, max(max(40, int(bt * 2.0)), ry1 - int(bt * 0.7))), cv2.FONT_HERSHEY_SIMPLEX, fs, color, ft)
            #cv2.imwrite("detections.png", outimg)
    else:
        check_line_crossing(list(), line_y)
    return crossed_flag, final_dets, outimg


def init(image, modelPaths):
    global blob, sessions, session_names, model_keys, saved_profiles, sesIndex, prev_tracked, flag_map
    if not modelPaths:
        print("ERROR: No models given!")
        return 0
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sessions = tuple(ort.InferenceSession(p, sess_options=opts, providers=providers) for p in modelPaths)
    session_names = list()
    model_keys = tuple(os.path.basename(p) for p in modelPaths)
    sesIndex = -1
    prev_tracked = list()
    flag_map = dict()
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            saved_profiles = json.load(f)
    else:
        saved_profiles = dict()
    next_flag = 0
    for idx, sesh in enumerate(sessions):
        meta = sesh.get_modelmeta().custom_metadata_map
        raw_names = meta.get("names")
        parsed = ast.literal_eval(raw_names) if raw_names else ({0: f"Model_{idx}"},)
        session_names.append(parsed)
        for b_idx in range(len(sesh.get_outputs())):
            if isinstance(parsed, (list, tuple)) and b_idx < len(parsed):
                entry = parsed[b_idx]
            elif isinstance(parsed, dict):
                entry = parsed
            else:
                entry = {0: str(parsed)}
            cids = tuple(entry.keys()) if isinstance(entry, dict) else (0,)
            for cid in cids:
                flag_map[(idx, b_idx, int(cid))] = next_flag
                print(f"Flag {next_flag} -> {resolve_branch_name(parsed, b_idx, int(cid))}")
                next_flag += 1
    resized = cv2.resize(image, (640, 640))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    blob = np.expand_dims(np.transpose(np.ascontiguousarray(rgb, dtype=np.float32) / 255.0, (2, 0, 1)), 0)
    for s in sessions:
        iname = next(iter(s.get_inputs())).name
        s.run(None, {iname: blob})
        s.run(None, {iname: blob})
    findobj(image)
    return 1
