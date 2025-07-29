import os
import subprocess
from typing import Dict, List, Optional, Union

class VideoFilterEngine:

    def __init__(self):
        self.filter_presets = {
            'none': {
                'name': 'No Filter',
                'filters': []
            },
            'cinematic': {
                'name': 'Cinematic',
                'filters': [
                    'curves=r=\'0/0 0.5/0.4 1/1\':g=\'0/0 0.5/0.4 1/1\':b=\'0/0 0.5/0.5 1/1\'',
                    'eq=contrast=1.2:brightness=0.05:saturation=1.1'
                ]
            },
            'warm': {
                'name': 'Warm & Cozy',
                'filters': [
                    'colorbalance=rs=0.2:gs=0:bs=-0.2',
                    'eq=contrast=1.1:brightness=0.1:saturation=1.2'
                ]
            },
            'cool': {
                'name': 'Cool & Modern',
                'filters': [
                    'colorbalance=rs=-0.2:gs=0:bs=0.2',
                    'eq=contrast=1.15:brightness=0.05:saturation=1.1'
                ]
            },
            'vintage': {
                'name': 'Vintage',
                'filters': [
                    'curves=r=\'0/0.1 0.5/0.5 1/0.9\':g=\'0/0.1 0.5/0.45 1/0.9\':b=\'0/0.2 0.5/0.4 1/0.8\'',
                    'eq=contrast=1.3:brightness=0.15:saturation=0.8'
                ]
            },
            'high_contrast': {
                'name': 'High Contrast',
                'filters': [
                    'eq=contrast=1.4:brightness=0.1:saturation=1.2',
                    'curves=all=\'0/0 0.3/0.2 0.7/0.8 1/1\''
                ]
            },
            'soft': {
                'name': 'Soft & Dreamy',
                'filters': [
                    'eq=contrast=0.9:brightness=0.2:saturation=1.1',
                    'gblur=sigma=0.5'
                ]
            },
            'vibrant': {
                'name': 'Vibrant',
                'filters': [
                    'eq=contrast=1.2:brightness=0.1:saturation=1.4',
                    'colorbalance=rs=0.1:gs=0.1:bs=0'
                ]
            },
            'black_white': {
                'name': 'Black & White',
                'filters': [
                    'hue=s=0',
                    'eq=contrast=1.2:brightness=0.1'
                ]
            },
            'sepia': {
                'name': 'Sepia',
                'filters': [
                    'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131',
                    'eq=contrast=1.1:brightness=0.1'
                ]
            }
        }

    def get_filter_presets(self) -> Dict[str, Dict]:
        return self.filter_presets

    def get_preset_names(self) -> List[str]:
        return list(self.filter_presets.keys())

    def build_custom_filter(self, 
                           brightness: float = 0.0,
                           contrast: float = 1.0, 
                           saturation: float = 1.0,
                           hue: float = 0.0,
                           gamma: float = 1.0,
                           highlights: float = 0.0,
                           shadows: float = 0.0,
                           warmth: float = 0.0,
                           sharpness: float = 0.0,
                           blur: float = 0.0) -> List[str]:

        filters = []
        
        if brightness != 0.0 or contrast != 1.0 or saturation != 1.0 or gamma != 1.0:
            filters.append(f'eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma}')
        
        if hue != 0.0:
            filters.append(f'hue=h={hue}')
        
        if warmth != 0.0:
            rs = warmth * 0.3
            bs = -warmth * 0.3
            filters.append(f'colorbalance=rs={rs}:bs={bs}')
        
        if highlights != 0.0 or shadows != 0.0:
            shadow_lift = max(0, shadows * 0.2)
            highlight_gain = 1 + (highlights * 0.3)
            curve_points = f'0/{shadow_lift} 0.5/0.5 1/{highlight_gain}'
            filters.append(f'curves=all=\'{curve_points}\'')
        
        if sharpness > 0.0:
            filters.append(f'unsharp=5:5:{sharpness}:5:5:0.0')
        
        if blur > 0.0:
            filters.append(f'gblur=sigma={blur}')
        
        return filters

    def apply_filter_preset(self, 
                           input_video: str, 
                           output_video: str, 
                           preset_name: str = 'none',
                           custom_settings: Optional[Dict] = None,
                           quality_preset: str = 'veryfast') -> bool:

        try:
            if not os.path.exists(input_video):
                print(f"Input video not found: {input_video}")
                return False

            filters = []
            
            if preset_name in self.filter_presets:
                filters.extend(self.filter_presets[preset_name]['filters'])
                print(f"Applying filter preset: {self.filter_presets[preset_name]['name']}")
            
            if custom_settings:
                custom_filters = self.build_custom_filter(**custom_settings)
                filters.extend(custom_filters)
                print(f"Applying custom filter settings: {custom_settings}")
            
            if not filters:
                cmd = [
                    'ffmpeg', '-i', input_video,
                    '-c:v', 'libx264',
                    '-preset', quality_preset,
                    '-crf', '23',
                    '-c:a', 'copy',
                    '-movflags', '+faststart',
                    '-y', output_video
                ]
                print("No filters applied, copying video...")
            else:
                filter_chain = ','.join(filters)
                
                cmd = [
                    'ffmpeg', '-i', input_video,
                    '-vf', filter_chain,
                    '-c:v', 'libx264',
                    '-preset', quality_preset,
                    '-crf', '23',
                    '-c:a', 'copy',
                    '-movflags', '+faststart',
                    '-threads', '2',
                    '-y', output_video
                ]
                print(f"Applying filter chain: {filter_chain}")
                print(f"Input: {input_video}, Output: {output_video}")
            
            print(f"Filter processing: {input_video} → {output_video}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"Filter applied successfully: {output_video}")
                return True
            else:
                print(f"Filter application failed: {result.stderr[-500:]}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Filter application timed out")
            return False
        except Exception as e:
            print(f"Filter application error: {e}")
            return False

    def apply_filters_to_video(self,
                              input_video: str,
                              output_video: str, 
                              filter_settings: Dict) -> bool:

        preset_name = filter_settings.get('preset', 'none')
        custom_settings = filter_settings.get('custom', {})
        quality = filter_settings.get('quality', 'veryfast')
        
        return self.apply_filter_preset(
            input_video=input_video,
            output_video=output_video,
            preset_name=preset_name,
            custom_settings=custom_settings,
            quality_preset=quality
        )

filter_engine = VideoFilterEngine()

def apply_video_filters(input_video: str, 
                       output_video: str, 
                       filter_settings: Dict) -> bool:

    return filter_engine.apply_filters_to_video(input_video, output_video, filter_settings)

def get_available_presets() -> Dict[str, str]:

    presets = filter_engine.get_filter_presets()
    return {key: value['name'] for key, value in presets.items()} 