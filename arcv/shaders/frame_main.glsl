// Common main loop: evaluate frameShape() for every active box and accumulate.

void main() {
    vec2 px = v_uv * u_resolution;
    float alpha = 0.0;
    for (int i = 0; i < 16; i++) {
        if (i >= u_count) break;
        float prog = u_meta[i].x;
        if (prog <= 0.001) continue;
        vec2 c = u_boxes[i].xy * u_resolution;
        vec2 hs = u_boxes[i].zw * u_resolution;
        alpha = max(alpha, frameShape(px, c, hs, prog));
    }
    if (alpha <= 0.001) discard;
    fragColor = vec4(u_color * alpha, alpha);
}
