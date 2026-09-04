use tauri::image::Image;

pub fn generate_shield_icon(state: &str, fill_percentage: f32) -> Image<'static> {
    const SIZE: usize = 32;
    let mut rgba = vec![0u8; SIZE * SIZE * 4];

    // Determine colors
    let (fill_color, actual_fill) = match state {
        "paused" => ([128u8, 128, 128, 255], 1.0f32),
        "saving" => ([0u8, 120, 212, 255], 1.0f32),
        "error" => ([211u8, 47, 47, 255], 1.0f32),
        "inactive" => ([135u8, 71, 255, 255], 1.0f32),
        _ => {
            // Normal state
            let col = if fill_percentage <= 0.25 {
                [40u8, 167, 69, 255] // Green
            } else if fill_percentage <= 0.50 {
                [255u8, 193, 7, 255] // Yellow
            } else {
                [220u8, 53, 69, 255] // Red
            };
            (col, fill_percentage.clamp(0.0, 1.0))
        }
    };

    let outline_color = [255u8, 255, 255, 255]; // White outline for tray

    // U-shield geometry
    let cx = 15.5f32;
    let cy_center = 17.0f32;
    let outer_r = 10.0f32;
    let inner_r = 7.0f32;
    let top_y = 5.0f32;
    let bottom_max_y = 27.0f32;

    let fill_height = (bottom_max_y - top_y) * actual_fill;
    let fill_start_y = bottom_max_y - fill_height;

    for y in 0..SIZE {
        for x in 0..SIZE {
            let px = x as f32 + 0.5;
            let py = y as f32 + 0.5;

            let idx = (y * SIZE + x) * 4;

            // Check if inside outer shield
            let inside_outer = if py <= cy_center {
                px >= (cx - outer_r) && px <= (cx + outer_r) && py >= top_y
            } else {
                let dist_sq = (px - cx).powi(2) + (py - cy_center).powi(2);
                dist_sq <= outer_r.powi(2)
            };

            if !inside_outer {
                continue;
            }

            // Check if inside inner cavity
            let inside_inner = if py <= cy_center {
                px >= (cx - inner_r) && px <= (cx + inner_r) && py >= top_y
            } else {
                let dist_sq = (px - cx).powi(2) + (py - cy_center).powi(2);
                dist_sq <= inner_r.powi(2)
            };

            if inside_inner {
                // Interior of shield: check fill
                if py >= fill_start_y && actual_fill > 0.0 {
                    rgba[idx..idx + 4].copy_from_slice(&fill_color);
                } else {
                    // Empty interior: translucent dark fill for visibility
                    rgba[idx..idx + 4].copy_from_slice(&[30, 35, 45, 160]);
                }
            } else {
                // Outline border of the U-shield
                rgba[idx..idx + 4].copy_from_slice(&outline_color);
            }
        }
    }

    Image::new_owned(rgba, SIZE as u32, SIZE as u32)
}
