# mrePy

**Installation:**

1. Clone the repository:
   ```sh
   git clone https://github.com/dstvx/mrePy.git
   ```
2. Navigate to the project directory:
   ```sh
   cd mrePy
   ```
3. Install the required Python packages:
   ```sh
   pip install -r requirements.txt
   ```

**Usage:**

```sh
python mrePy.py [options]
```

**Modes:**
- `--create`: Create a modpack archive from a Minecraft folder.
- `--get`: Extract and process a .mrpack archive.

**Options:**
- `-i, --input`: Input path (Minecraft folder for `--create` mode, .mrpack archive for `--get` mode).
- `-o, --output`: Output path (output .mrpack archive for `--create` mode, output directory for `--get` mode).
- `-fo, --force-override`: Force override files without asking for confirmation.
- `-sh, --skip-hash`: Skip hash verification.

**Example Usage:**

1. Create a modpack archive:
   ```sh
   python mrePy.py --create -i "/path/to/.minecraft" -o "/output/path/modpack.mrpack" -fo
   ```

2. Extract and process a .mrpack archive:
   ```sh
   python mrePy.py --get -i "/path/to/modpack.mrpack" -o "/output/directory" -sh
   ```

**Installation from Releases:**

1. Go to the [Releases](https://github.com/your-username/mrePy/releases/latest) page.
2. Download the latest release.
3. Run `mrePy.exe`.

**Note:** Ensure that you have the required dependencies installed or included in the same directory as the executable for proper functioning.
