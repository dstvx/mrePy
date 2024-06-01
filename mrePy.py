import argparse
from pathlib import Path
from requests import get as _get
from zipfile import ZipFile
from shutil import move, rmtree, copytree as _copytree, copy2 as _copy2, make_archive
from colorama import Fore as F, init
from fake_useragent import UserAgent
from json import load, dump as _dump
from hashlib import sha1 as _sha1, sha512 as _sha512
from os import walk as _walk
from typing import List

init()

# Constants
CWD = Path.cwd()
DEFAULT_OUTPUT_FOLDER = CWD / "Result"
TMP_FOLDER = CWD / "tmp"
MODRINTH_API_URL = 'https://api.modrinth.com/v2/version_file/{}'
FABRIC_LOADER_RELEASES_URL = 'https://api.github.com/repos/FabricMC/fabric-loader/releases/latest'
DEFAULT_VERSION_ID = '1.0.0'
DEFAULT_NAME = 'Custom Modpack'
DEFAULT_SUMMARY = 'Automatically generated modpack'

# Colors
GREEN = F.LIGHTGREEN_EX + '{}' + F.RESET
BOLD_GREEN = F.LIGHTGREEN_EX + '\033[1m{}\033[0m' + F.RESET
RED = F.LIGHTRED_EX + '{}' + F.RESET
BOLD_RED = F.LIGHTRED_EX + '\033[1m{}\033[0m' + F.RESET
YELLOW = F.LIGHTYELLOW_EX + '{}' + F.RESET
BOLD_YELLOW = F.LIGHTYELLOW_EX + '\033[1m{}\033[0m' + F.RESET
WHITE = F.LIGHTWHITE_EX + '{}' + F.RESET
BOLD_WHITE = F.LIGHTWHITE_EX + '\033[1m{}\033[0m' + F.RESET

def unzipArchive(src: Path, dst: Path) -> None:
    """Unzips the archive from src to dst."""
    with ZipFile(src, 'r') as f:
        f.extractall(dst)

def createOutputFolder(output_dir: Path) -> Path:
    """Creates the output folder if it doesn't exist."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def createArchive(input_files: List[Path], output_file: Path) -> None:
    """Creates a zip archive from the input files."""
    with ZipFile(output_file, 'w') as archive:
        for file in input_files:
            archive.write(file, file.relative_to(TMP_FOLDER))

def downloadFile(url: str, file_path: Path) -> None:
    """Downloads a file from the given URL to the specified file path."""
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    response = _get(url, headers=headers, stream=True)
    with file_path.open('wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def verifyHash(file_path: Path, expected_hashes: dict) -> bool:
    """Verifies the file's hash against the expected hashes."""
    sha1 = _sha1()
    sha512 = _sha512()

    with file_path.open('rb') as file:
        while True:
            data = file.read(65536)
            if not data:
                break
            sha1.update(data)
            sha512.update(data)

    sha1_hash = sha1.hexdigest()
    sha512_hash = sha512.hexdigest()

    return (sha1_hash == expected_hashes['sha1']) and (sha512_hash == expected_hashes['sha512'])

def getArchive(input_file: Path, output_dir: Path, skip_hash: bool) -> None:
    """Extracts and processes a .mrpack archive."""
    if input_file.suffix != ".mrpack":
        raise ValueError(f"Invalid file format: {input_file.name} is not a valid .mrpack file.")

    createOutputFolder(TMP_FOLDER)
    unzipArchive(input_file, TMP_FOLDER)

    with (TMP_FOLDER / "modrinth.index.json").open('r') as file:
        index_data = load(file)

    print(BOLD_WHITE.format(f"Modpack: {index_data['name']}"))
    print(WHITE.format(f"Version ID: {index_data['versionId']}"))
    print(WHITE.format(f"Summary: {index_data['summary']}"))
    print(WHITE.format(f"Minecraft Version: {index_data['dependencies']['minecraft']}"))
    print(WHITE.format(f"Fabric Loader Version: {index_data['dependencies']['fabric-loader']}"))

    minecraft_folder = TMP_FOLDER / ".minecraft"
    minecraft_folder.mkdir(exist_ok=True)

    # Move contents of overrides folder to .minecraft
    overrides_folder = TMP_FOLDER / "overrides"
    if overrides_folder.exists():
        for item in overrides_folder.iterdir():
            if item.is_dir():
                _copytree(item, minecraft_folder / item.name, dirs_exist_ok=True)
            else:
                _copy2(item, minecraft_folder)

    for file_info in index_data['files']:
        file_path = minecraft_folder / Path(file_info['path'])
        file_path.parent.mkdir(parents=True, exist_ok=True)

        url = file_info['downloads'][0]
        print(YELLOW.format(f"Downloading: {file_path.name}"))
        downloadFile(url, file_path)

        if not skip_hash and not verifyHash(file_path, file_info['hashes']):
            file_path.unlink()
            print(BOLD_RED.format(f"Hash verification failed for {file_path.name}"))
        else:
            print(GREEN.format(f"Hash verification succeeded for {file_path.name}"))

    output_modpack_dir = createOutputFolder(output_dir / input_file.stem)
    try:
        print('Moving files to', BOLD_YELLOW.format(f'{output_modpack_dir}' + '...'))
        move(str(minecraft_folder), str(output_modpack_dir))
    except Exception as e:
        print(BOLD_RED.format(f"Error: {e}"))
        print(BOLD_RED.format("The destination folder already exists. Please choose a different output folder or delete the existing one."))
        return

    print('Removing temporary files...')
    rmtree(TMP_FOLDER)
    print(BOLD_GREEN.format('Done!'))

def getLatestLoader() -> str:
    """Fetches the latest version of the Fabric Loader from the GitHub API.
    
    Returns:
        str: The tag name of the latest Fabric Loader release, or None if the request failed.
    """
    response = _get(FABRIC_LOADER_RELEASES_URL)
    if response.status_code == 200:
        return response.json()['tag_name']
    else:
        print(f"{RED}Failed to fetch Fabric Loader version. Status code: {response.status_code}{F.RESET}")
        return None

def getFileHashFromAPI(file_path: Path, algorithm: str) -> str:
    """Fetches the hash of a file from the Modrinth API."""
    hash_value = _sha512(file_path.read_bytes()).hexdigest() if algorithm == 'sha512' else _sha1(file_path.read_bytes()).hexdigest()
    url = MODRINTH_API_URL.format(hash_value)
    params = {'algorithm': algorithm, 'multiple': True}
    response = _get(url, params=params)

    if response.status_code == 200:
        for file_info in response.json().get('files', []):
            if file_info['filename'] == str(file_path.name):
                return file_info['hashes'][algorithm]
    elif response.status_code == 404:
        raise ValueError(f"File '{file_path}' not found on Modrinth API.")
    else:
        raise ValueError(f"Failed to fetch file hash from Modrinth API. Status code: {response.status_code}")

    return None

def createModpackArchive(minecraft_folder: Path, output_file: Path, version_id: str, modpack_name: str, summary: str,
                         minecraft_version: str, fabric_loader_version: str, force_override: bool) -> None:
    """Creates a modpack archive from the specified Minecraft folder."""
    TMP_FOLDER.mkdir(parents=True, exist_ok=True)

    include_config = force_override or input(YELLOW.format("Include 'config' folder? (y/n) ")).lower() == 'y'
    include_resourcepacks = force_override or input(YELLOW.format("Include 'resourcepacks' folder? (y/n) ")).lower() == 'y'
    include_mods = force_override or input(YELLOW.format("Include 'mods' folder? (y/n) ")).lower() == 'y'
    include_shaderpacks = force_override or input(YELLOW.format("Include 'shaderpacks' folder? (y/n) ")).lower() == 'y'

    allowed_folders = ['config', 'resourcepacks', 'mods', 'shaderpacks']
    included_folders = [folder for folder in allowed_folders
                        if (folder == 'config' and include_config) or
                        (folder == 'resourcepacks' and include_resourcepacks) or
                        (folder == 'mods' and include_mods) or
                        (folder == 'shaderpacks' and include_shaderpacks)]

    override_folder = TMP_FOLDER / "overrides"
    override_folder.mkdir(parents=True, exist_ok=True)

    modrinth_index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": version_id,
        "name": modpack_name,
        "summary": summary,
        "files": [],
        "dependencies": {
            "minecraft": minecraft_version or None,
            "fabric-loader": fabric_loader_version or None
        }
    }

    for root, _, files in _walk(minecraft_folder):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(minecraft_folder)

            if rel_path.parts[0] not in allowed_folders:
                continue

            if rel_path.parts[0] == 'config':
                print(BOLD_GREEN.format(f"Adding config file '{rel_path}' as override."))
                override_file_path = override_folder / rel_path
                override_file_path.parent.mkdir(parents=True, exist_ok=True)
                _copy2(file_path, override_file_path)
                continue

            hashes = {
                'sha1': _sha1(file_path.read_bytes()).hexdigest(),
                'sha512': _sha512(file_path.read_bytes()).hexdigest()
            }

            print(YELLOW.format(f"Checking {rel_path} in the API..."))
            try:
                hash_from_api = getFileHashFromAPI(file_path, 'sha512')
                print(GREEN.format(f"File '{rel_path}' found in the API."))
                modrinth_index['files'].append({
                    'path': str(rel_path).replace("\\", "/"),
                    'hashes': hashes,
                    'downloads': [f"https://cdn.modrinth.com/data/{str(rel_path).replace('\\', '/')}"]
                })
            except ValueError as e:
                print(BOLD_RED.format(str(e)))
                if force_override or input(YELLOW.format(f"Add '{rel_path}' as override? (y/n) ")).lower() == 'y':
                    print(BOLD_GREEN.format(f"Adding '{rel_path}' as override."))
                    override_file_path = override_folder / rel_path
                    override_file_path.parent.mkdir(parents=True, exist_ok=True)
                    _copy2(file_path, override_file_path)
                else:
                    continue

    with (TMP_FOLDER / "modrinth.index.json").open('w') as file:
        _dump(modrinth_index, file, indent=4)

    createArchive([TMP_FOLDER / "modrinth.index.json", override_folder], output_file)
    rmtree(TMP_FOLDER)
    print(BOLD_GREEN.format("Modpack archive created successfully!"))

def main():
    """Main function to handle command-line arguments and execute the appropriate mode."""
    parser = argparse.ArgumentParser(description="Manage .mrpack archives.")
    parser.add_argument('-m', '--mode', required=True, choices=['create', 'get'], help="Mode (create or get).")
    parser.add_argument('-i', '--input', nargs='+', type=Path, help="Input .minecraft folder for 'create' mode, or .mrpack archive for 'get' mode.")
    parser.add_argument('-o', '--output', type=Path, help="Output .mrpack archive for 'create' mode, or output directory for 'get' mode.")
    parser.add_argument('-v', '--version-id', type=str, default=DEFAULT_VERSION_ID, help="Version ID for the modpack (create mode).")
    parser.add_argument('-n', '--name', type=str, default=DEFAULT_NAME, help="Name of the modpack (create mode).")
    parser.add_argument('-s', '--summary', type=str, default=DEFAULT_SUMMARY, help="Summary description of the modpack (create mode).")
    parser.add_argument('-mc', '--minecraft-version', type=str, help="Minecraft version for the modpack (create mode).")
    parser.add_argument('-fo', '--force-override', action='store_true', help="Force override without prompting the user (create mode).")

    args = parser.parse_args()

    if args.mode == 'create':
        if not args.output:
            args.output = DEFAULT_OUTPUT_FOLDER / "output.mrpack"
        args.output.parent.mkdir(parents=True, exist_ok=True)

        fabric_loader_version = getLatestLoader()
        if not fabric_loader_version:
            print(BOLD_RED.format("Error: Failed to fetch the latest Fabric Loader version."))
            return

        createModpackArchive(args.input[0], args.output, args.version_id, args.name, args.summary, args.minecraft_version, fabric_loader_version, args.force_override)
    elif args.mode == 'get':
        if not args.output:
            args.output = DEFAULT_OUTPUT_FOLDER
        getArchive(args.input[0], args.output, args.skip_hash)
        print(BOLD_GREEN.format("Modpack retrieved successfully!"))

if __name__ == "__main__":
    main()

# https://github.com/dstvx/mrePy.git