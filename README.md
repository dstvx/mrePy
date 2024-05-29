# mrePy

**Installation:**

1. Clone the repository:
   ```sh
   git clone https://github.com/your-username/mrePy.git
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
python mrePy.py -m <mode> [options]
```

**Modes:**
- `create`: Create a modpack archive from a Minecraft folder.
- `get`: Extract and process a .mrpack archive.

**Options:**
- `-i, --input`: Input path (Minecraft folder for `create` mode, .mrpack archive for `get` mode).
- `-o, --output`: Output path (output .mrpack archive for `create` mode, output directory for `get` mode).
- `-v, --version-id`: Version ID for the modpack (create mode).
- `-n, --name`: Name of the modpack (create mode).
- `-s, --summary`: Summary description of the modpack (create mode).
- `-mc, --minecraft-version`: Minecraft version for the modpack (create mode).
- `-fo, --force-override`: Force override files without asking for confirmation.

**Example Usage:**

1. Create a modpack archive:
   ```sh
   python mrePy.py -m create -i "/path/to/.minecraft" -o "/output/path/modpack.mrpack" -v "1.0.0" -n "Custom Modpack" -s "Automatically generated modpack" -mc "1.17.1"
   ```

2. Extract and process a .mrpack archive:
   ```sh
   python mrePy.py -m get -i "/path/to/modpack.mrpack" -o "/output/directory"
   ```

**Installation from Releases:**

1. Go to the [Releases](https://github.com/your-username/mrePy/releases) page.
2. Download the latest release.
3. Extract the contents of the downloaded zip file.
4. Run `myscript.exe` from the extracted folder.

**Note:** Ensure that you have the required dependencies installed or included in the same directory as the executable for proper functioning.
