#version 330

// Final composite: graded camera + HUD + additive bloom, then the animated
// scanline overlay, a sweep band, vignette, and exposure tone-map to LDR.

in vec2 v_uv;
out vec4 fragColor;

uniform sampler2D u_scene;   // graded camera
uniform sampler2D u_hud;     // HUD geometry
uniform sampler2D u_bloom;   // blurred glow
uniform float u_time;
uniform float u_bloom_intensity;
uniform vec3 u_glow;         // bloom tint (#6ff)
uniform float u_scan_count;
uniform float u_scan_strength;
uniform float u_sweep_speed;
uniform float u_sweep_strength;
uniform float u_exposure;

void main() {
    vec3 scene = texture(u_scene, v_uv).rgb;
    vec3 hud = texture(u_hud, v_uv).rgb;
    vec3 bloom = texture(u_bloom, v_uv).rgb * u_glow * u_bloom_intensity;

    vec3 col = scene + hud + bloom;

    // static scanline bands
    float bands = 0.5 + 0.5 * sin(v_uv.y * u_scan_count * 3.14159265);
    col *= (1.0 - u_scan_strength * (1.0 - bands));

    // moving sweep band
    float sweep = fract(u_time * u_sweep_speed);
    col += u_glow * smoothstep(0.05, 0.0, abs(v_uv.y - sweep)) * u_sweep_strength;

    // vignette
    float vig = smoothstep(0.85, 0.32, length(v_uv - 0.5));
    col *= mix(0.72, 1.0, vig);

    // exposure tone-map
    col = vec3(1.0) - exp(-col * u_exposure);
    fragColor = vec4(col, 1.0);
}
