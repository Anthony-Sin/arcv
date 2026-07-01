#version 330

// Anti-aliased stroke / fill. `v_edge` runs -1..1 across a stroke; fills pass 0
// with a large half-width so they stay fully opaque.

in vec4 v_color;
in float v_edge;
in float v_hw;
out vec4 fragColor;

void main() {
    float feather = clamp(1.5 / max(v_hw, 1.0), 0.0, 1.0);
    float a = 1.0 - smoothstep(1.0 - feather, 1.0, abs(v_edge));
    float alpha = v_color.a * a;
    if (alpha <= 0.003) discard;
    fragColor = vec4(v_color.rgb * alpha, alpha);  // premultiplied for additive
}
