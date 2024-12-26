import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar, Style
from threading import Thread


class M4BConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MP3 to M4B Converter")
        self.root.geometry("600x600")
        self.root.resizable(False, False)

        # Color scheme
        self.root.configure(bg="#002b36")
        self.text_color = "#839496"
        self.highlight_color = "#268bd2"

        # Stop flag and FFmpeg process handle
        self.stop_flag = False
        self.ffmpeg_process = None  # Reference to the current FFmpeg process

        # Style for progress bars
        style = Style()
        style.theme_use("default")
        style.configure("Horizontal.TProgressbar", thickness=20, background=self.highlight_color)

        # Folder selection
        tk.Label(root, text="Select folder with MP3 files:", font=("Arial", 12), bg="#002b36", fg=self.text_color).pack(pady=10)
        folder_frame = tk.Frame(root, bg="#002b36")
        folder_frame.pack(pady=5)
        self.folder_path = tk.StringVar()
        tk.Entry(folder_frame, textvariable=self.folder_path, width=40, font=("Arial", 10), bg="#073642", fg=self.text_color, insertbackground=self.text_color).pack(side=tk.LEFT, padx=5)
        tk.Button(folder_frame, text="Browse", command=self.select_folder, bg=self.highlight_color, fg="#002b36", font=("Arial", 10)).pack(side=tk.LEFT)

        # Start and Stop buttons
        button_frame = tk.Frame(root, bg="#002b36")
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Start Conversion", command=self.start_conversion_thread, bg=self.highlight_color, fg="#002b36", font=("Arial", 12)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Stop", command=self.stop_conversion, bg="#d33682", fg="#002b36", font=("Arial", 12)).pack(side=tk.LEFT, padx=10)

        # Current task label
        self.current_task_label = tk.Label(root, text="Idle", font=("Arial", 12), bg="#002b36", fg=self.text_color)
        self.current_task_label.pack(pady=5)

        # Overall progress bar
        tk.Label(root, text="Overall Progress:", font=("Arial", 12), bg="#002b36", fg=self.text_color).pack(pady=5)
        self.progress = Progressbar(root, orient="horizontal", length=500, mode="determinate", style="Horizontal.TProgressbar")
        self.progress.pack(pady=5)
        self.progress_label = tk.Label(root, text="0%", font=("Arial", 10), bg="#002b36", fg=self.text_color)
        self.progress_label.pack(pady=5)

        # Detailed progress bar
        tk.Label(root, text="Current Step Progress:", font=("Arial", 12), bg="#002b36", fg=self.text_color).pack(pady=5)
        self.detail_progress = Progressbar(root, orient="horizontal", length=500, mode="determinate", style="Horizontal.TProgressbar")
        self.detail_progress.pack(pady=5)
        self.detail_progress_label = tk.Label(root, text="0%", font=("Arial", 10), bg="#002b36", fg=self.text_color)
        self.detail_progress_label.pack(pady=5)

        # Log area
        tk.Label(root, text="Log:", font=("Arial", 12), bg="#002b36", fg=self.text_color).pack(pady=10)
        self.log_text = tk.Text(root, width=70, height=10, state="disabled", bg="#073642", fg=self.text_color, insertbackground=self.text_color)
        self.log_text.pack(pady=5)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def start_conversion_thread(self):
        folder = self.folder_path.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid folder with MP3 files.")
            return

        # Reset progress bars and log
        self.reset_progress()
        self.stop_flag = False

        # Start conversion in a separate thread
        self.thread = Thread(target=self.start_conversion, args=(folder,))
        self.thread.start()

    def stop_conversion(self):
        """Stops the conversion process and cleans up."""
        self.stop_flag = True
        self.set_current_task("Stopping...")
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            # Forcefully terminate the FFmpeg process using taskkill
            subprocess.run(f"taskkill /F /PID {self.ffmpeg_process.pid} /T", shell=True)
            self.log("FFmpeg process terminated.")
        self.cleanup_temp_files()  # Remove temporary files
        self.reset_progress()

    def cleanup_temp_files(self):
        """Deletes temporary files created during conversion."""
        folder = self.folder_path.get()
        if not folder:
            return
        temp_files = ["combined.mp3", "filelist.txt"]
        for temp_file in temp_files:
            temp_path = os.path.join(folder, temp_file)
            if os.path.exists(temp_path):
                os.remove(temp_path)
                self.log(f"Deleted temporary file: {temp_file}")

    def reset_progress(self):
        """Resets progress bars and log to initial state."""
        self.progress["value"] = 0
        self.detail_progress["value"] = 0
        self.progress_label.config(text="0%")
        self.detail_progress_label.config(text="0%")
        self.current_task_label.config(text="Idle")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def start_conversion(self, folder):
        try:
            total_steps = 4
            current_step = 0

            # Step 1: Create file list
            self.set_current_task("Creating file list...")
            self.log("Creating file list...")
            if self.stop_flag: return
            filelist_path = os.path.join(folder, "filelist.txt")
            input_files = [os.path.join(folder, file) for file in sorted(os.listdir(folder)) if file.endswith(".mp3")]
            with open(filelist_path, "w") as filelist:
                for file in input_files:
                    filelist.write(f"file '{file}'\n")
            self.log("File list created.")
            current_step += 1
            self.update_progress(current_step, total_steps)

            # Step 2: Combine MP3 files
            self.set_current_task("Combining MP3 files...")
            combined_mp3 = os.path.join(folder, "combined.mp3")
            self.log("Combining MP3 files into combined.mp3...")
            if self.stop_flag: return
            ffmpeg_concat_cmd = f'ffmpeg -f concat -safe 0 -i "{filelist_path}" -c copy -threads 0 "{combined_mp3}"'
            self.run_ffmpeg_with_progress(ffmpeg_concat_cmd, combined_mp3, input_files)
            self.log("MP3 files combined.")
            current_step += 1
            self.update_progress(current_step, total_steps)

            # Step 3: Convert to M4B
            self.set_current_task("Converting to M4B...")
            output_m4b = os.path.join(folder, "output.m4b")
            self.log("Converting to M4B...")
            if self.stop_flag: return
            ffmpeg_convert_cmd = f'ffmpeg -i "{combined_mp3}" -codec:a aac -b:a 64k -vn -threads 0 "{output_m4b}"'
            self.run_ffmpeg_with_progress(ffmpeg_convert_cmd, output_m4b, [combined_mp3])
            self.log("File converted to M4B.")
            current_step += 1
            self.update_progress(current_step, total_steps)

            # Step 4: Cleanup
            self.set_current_task("Cleaning up...")
            if self.stop_flag: return
            os.remove(filelist_path)
            os.remove(combined_mp3)
            self.log("Temporary files removed.")
            current_step += 1
            self.update_progress(current_step, total_steps)

            # Finish
            self.set_current_task("Done")
            self.log("Conversion completed successfully!")
            messagebox.showinfo("Success", f"File output.m4b created in:\n{folder}")
        except subprocess.CalledProcessError as e:
            self.log(f"FFmpeg error: {e}")
            messagebox.showerror("Error", "An error occurred while processing the files.")
        except Exception as e:
            self.log(f"General error: {e}")
            messagebox.showerror("Error", "An unexpected error occurred.")
        finally:
            self.update_progress(total_steps, total_steps)

    def run_ffmpeg_with_progress(self, command, output_file, input_files):
        total_size = sum(os.path.getsize(f) for f in input_files)  # Total size of input files
        self.ffmpeg_process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        while True:
            if self.stop_flag:
                subprocess.run(f"taskkill /F /PID {self.ffmpeg_process.pid} /T", shell=True)
                return

            # Check the size of the output file
            if os.path.exists(output_file):
                current_size = os.path.getsize(output_file)
                progress = min((current_size / total_size) * 100, 100)  # Calculate progress
                self.detail_progress["value"] = progress
                self.detail_progress_label.config(text=f"{int(progress)}%")
                self.root.update_idletasks()

            line = self.ffmpeg_process.stderr.readline()
            if not line:
                break
            self.log(line.strip())

        self.ffmpeg_process.wait()  # Wait for FFmpeg process to complete
        if self.ffmpeg_process.returncode != 0 and not self.stop_flag:
            raise subprocess.CalledProcessError(self.ffmpeg_process.returncode, command)

        # Ensure the progress shows 100% after completion
        self.detail_progress["value"] = 100
        self.detail_progress_label.config(text="100%")
        self.root.update_idletasks()

    def set_current_task(self, task):
        """Updates the current task label."""
        self.current_task_label.config(text=task)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def update_progress(self, current_step, total_steps):
        progress = (current_step / total_steps) * 100
        self.progress["value"] = progress
        self.progress_label.config(text=f"{int(progress)}%")
        self.root.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    app = M4BConverterApp(root)
    root.mainloop()
