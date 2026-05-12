"""
wav_merger.py —— 将多个 WAV 片段合并为一个完整录音文件。
"""
import wave
import os


def read_wav(file_path):
    wav = wave.open(file_path, "rb")
    params = wav.getparams()
    frames = wav.readframes(wav.getnframes())
    wav.close()
    return params, frames


def merge_wav(wav_list, output_file):
    """
    将 wav_list 中的文件合并后写入 output_file。
    若 output_file 已存在，则追加到现有内容末尾。
    """
    print("run merge_wav")
    # `wav_list` is expected to contain full paths to chunk files.

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    merged_params = None
    merged_frames = b""
    for file in wav_list:
        params, frames = read_wav(file)
        if merged_params is None:
            merged_params = params
        merged_frames += frames

    if not merged_params:
        return

    if not os.path.exists(output_file):
        with wave.open(output_file, "wb") as out:
            out.setparams(merged_params)
            out.writeframes(merged_frames)
    else:
        params_existing, frames_existing = read_wav(output_file)
        combined_frames = frames_existing + merged_frames
        with wave.open(output_file, "wb") as out:
            out.setparams(params_existing)
            out.writeframes(combined_frames)
    print("merge_wav ok")
