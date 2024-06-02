from argparse import ArgumentParser
from os import system, name as osName
from colorama import Fore as F, init
from pathlib import Path
from typing import Dict, List, Union, Optional
from hashlib import sha1, sha512
from requests import get as _get, exceptions as requestsExceptions
from json import load, dump
from shutil import copytree, copy, rmtree, move
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent

# Initialize colorama
init()

# Constants
CWD = Path.cwd()
DEFAULT_OUTPUT_FOLDER = CWD / "Result"
TMP_FOLDER = CWD / "tmp"
OVERRIDES_FOLDER = TMP_FOLDER / 'overrides'
MODRINTH_API_URL = 'https://api.modrinth.com/v2/version_file/{}'
FABRIC_LOADER_RELEASES_URL = 'https://api.github.com/repos/FabricMC/fabric-loader/releases/latest'
DEFAULT_VERSION_ID = '1.0.0'
DEFAULT_NAME = 'Custom Modpack'
DEFAULT_SUMMARY = 'Automatically generated modpack'
CHUNK_SIZE = 1024 * 1024

# Color constants
GREEN = F.LIGHTGREEN_EX + '{}' + F.RESET
BOLD_GREEN = F.LIGHTGREEN_EX + '\033[1m{}\033[0m' + F.RESET
RED = F.LIGHTRED_EX + '{}' + F.RESET
BOLD_RED = F.LIGHTRED_EX + '\033[1m{}\033[0m' + F.RESET
YELLOW = F.LIGHTYELLOW_EX + '{}' + F.RESET
BOLD_YELLOW = F.LIGHTYELLOW_EX + '\033[1m{}\033[0m' + F.RESET
WHITE = F.LIGHTWHITE_EX + '{}' + F.RESET
BOLD_WHITE = F.LIGHTWHITE_EX + '\033[1m{}\033[0m' + F.RESET


def getUA():
    return {'User-Agent': UserAgent().random}

def cls():
    """Clears the console screen."""
    system('cls' if osName == 'nt' else 'clear')


def getLatestLoader() -> Optional[str]:
    """Fetches the latest version of the Fabric Loader from the GitHub API.

    Returns:
        Optional[str]: The tag name of the latest Fabric Loader release, or None if the request failed.
    """
    try:
        response = _get(FABRIC_LOADER_RELEASES_URL, headers=getUA())
        response.raise_for_status()
        return response.json().get('tag_name')
    except requestsExceptions.RequestException as e:
        print(RED.format(f"Failed to fetch Fabric Loader version: {e}"))
        return None


def getHashes(fp: Path) -> Dict[str, str]:
    """Computes the SHA-1 and SHA-512 hashes of a file.

    Args:
        fp (Path): The file path.

    Returns:
        Dict[str, str]: A dictionary with the SHA-1 and SHA-512 hashes.
    """
    sha1Hash = sha1()
    sha512Hash = sha512()
    with fp.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha1Hash.update(chunk)
            sha512Hash.update(chunk)
    return {'sha1': sha1Hash.hexdigest(), 'sha512': sha512Hash.hexdigest()}


def getFiles(folder: Path, child: str) -> List[Path]:
    """Gets a list of files in a specified subdirectory.

    Args:
        folder (Path): The parent folder.
        child (str): The subdirectory name.

    Returns:
        List[Path]: A list of file paths.
    """
    try:
        return list((folder / child).glob('*'))
    except Exception as e:
        print(RED.format(f"Error accessing files in {folder / child}: {e}"))
        return []


def createMrpack(src: Path, dst: Path):
    """Creates a zip archive (.mrpack) from the specified source folder.

    Args:
        src (Path): The source folder.
        dst (Path): The destination file path.
    """
    try:
        with ZipFile(dst, 'w') as archive:
            for file in src.rglob('*'):
                archive.write(file, file.relative_to(src))
        print(GREEN.format(f"Archive created successfully at {dst}"))
    except Exception as e:
        print(RED.format(f"Error creating archive {dst}: {e}"))


def deleteEmptyFolders(path: Path):
    """Deletes empty folders in the specified directory.

    Args:
        path (Path): The parent directory.
    """
    for folder in sorted(path.glob('**/*'), key=lambda p: -len(str(p).split('/'))):
        if folder.is_dir() and not any(folder.iterdir()):
            try:
                folder.rmdir()
                print(YELLOW.format(f"Deleted empty folder: {folder}"))
            except Exception as e:
                print(RED.format(f"Error deleting folder {folder}: {e}"))


def downloadFile(downloadUrl: str, filePath: Path, expectedHash: str) -> bool:
    """Downloads a file and verifies its SHA-1 hash.
    
    Args:
        downloadUrl (str): The URL to download the file from.
        filePath (Path): The path to save the file.
        expectedHash (str): The expected SHA-1 hash of the file.
        
    Returns:
        bool: True if the file was downloaded and verified successfully, otherwise False.
    """
    try:
        response = _get(downloadUrl, stream=True, headers=getUA())
        response.raise_for_status()

        with filePath.open('wb') as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                file.write(chunk)

        fileHash = sha1(filePath.read_bytes()).hexdigest()
        if fileHash == expectedHash:
            print(GREEN.format(f"Downloaded and verified {filePath.name} successfully."))
            return True
        else:
            print(RED.format(f"Hash mismatch for {filePath.name}."))
            return False
    except requestsExceptions.RequestException as e:
        print(RED.format(f"Error downloading {filePath.name}: {e}"))
        return False

def copyFiles(child: str, add: bool, folder: Path):
    """Copies files from a source folder to the overrides folder if required.
    
    Args:
        child (str): The subdirectory name.
        add (bool): Whether to add files from this subdirectory.
        folder (Path): The source folder.
    """
    if add:
        dest = OVERRIDES_FOLDER / child
        dest.mkdir(parents=True, exist_ok=True)
        for i in getFiles(folder=folder, child=child):
            if i.is_file():
                copy(i, dest)
            else:
                copytree(i, dest / i.name, dirs_exist_ok=True)


def copyFilesThreaded(child: str, add: bool, folder: Path):
    """Copies files from the source folder to the override folder using threads.

    Args:
        child (str): The subdirectory name.
        add (bool): Whether to add files from this subdirectory.
        folder (Path): The source folder.
    """
    if add:
        dest = OVERRIDES_FOLDER / child
        dest.mkdir(parents=True, exist_ok=True)
        files = getFiles(folder, child)
        
        def copyFile(src: Path):
            try:
                if src.is_file():
                    copy(src, dest)
                    print(GREEN.format(f"Copied file {src.name} to {dest}"))
                else:
                    copytree(src, dest / src.name, dirs_exist_ok=True)
                    print(GREEN.format(f"Copied directory {src.name} to {dest}"))
            except Exception as e:
                print(RED.format(f"Error copying {src.name}: {e}"))

        with ThreadPoolExecutor() as executor:
            executor.map(copyFile, files)


def getFileURL(fp: Path) -> Union[str, None]:
    """Gets the download URL of a file using its SHA-1 hash.

    Args:
        fp (Path): The path to the file.

    Returns:
        Union[str, None]: The download URL of the file, or None if not found.
    """
    hashes = getHashes(fp)
    r = _get(MODRINTH_API_URL.format(hashes['sha1']), headers=getUA())
    try:
        if r.status_code != 200:
            return None
        return r.json()['files'][0]['url']
    except:
        return None

def addFilesThreaded(child: str, add: bool, folder: Path, forced: bool, defaultIndex: Dict) -> None:
    """Adds files to the default index and copies them to the override folder using threads."""
    if add:
        dest = OVERRIDES_FOLDER / child
        dest.mkdir(parents=True, exist_ok=True)

        files = getFiles(folder, child)
        overrides = []  # List to store files to be potentially overridden
        
        def processFile(i: Path):
            hashes = getHashes(i)
            url = getFileURL(i)
            if not url:
                overrides.append(i)  # Collect the files to ask for override later
                return
            defaultIndex['files'].append({
                'path': f'{child}/{i.name}',
                'hashes': hashes,
                'downloads': [url] if url else [],
                'filesize': i.stat().st_size
            })
            print(GREEN.format(f"Added {i.name} to the index"))

        with ThreadPoolExecutor() as executor:
            executor.map(processFile, files)
        
        # After all threads are done, ask for overrides
        for i in overrides:
            override = forced or input(f'Add {i.name} as override? (y/n): ') == 'y'
            if override:
                copy(i, dest)
                print(GREEN.format(f"Added {i.name} as override"))


def createArchive(folder: Path, forced: Optional[bool] = None, outputFolder: Optional[Path] = None,
                  versionId: Optional[str] = None, modpackName: Optional[str] = None,
                  summary: Optional[str] = None, minecraftVersion: Optional[str] = None,
                  fabricLoaderVersion: Optional[str] = None):
    """Creates a modpack archive (.mrpack) from the specified folder.

    Args:
        folder (Path): The source folder.
        forced (Optional[bool]): If True, force add files without prompting.
        outputFolder (Optional[Path]): The output folder for the archive.
        versionId (Optional[str]): The modpack version ID.
        modpackName (Optional[str]): The modpack name.
        summary (Optional[str]): The modpack summary.
        minecraftVersion (Optional[str]): The Minecraft version.
        fabricLoaderVersion (Optional[str]): The Fabric loader version.
    """
    if forced:
        addConfig, addMods, addResourcepacks, addShaderpacks = True, True, True, True
    else:
        addConfig = input('Add config files? (y/n): ').lower() == 'y'
        addMods = input('Add mods files? (y/n): ').lower() == 'y'
        addResourcepacks = input('Add resourcepack files? (y/n): ').lower() == 'y'
        addShaderpacks = input('Add shaderpack files? (y/n): ').lower() == 'y'

    TMP_FOLDER.mkdir(exist_ok=True)
    OVERRIDES_FOLDER.mkdir(exist_ok=True)

    defaultIndex = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": versionId or DEFAULT_VERSION_ID,
        "name": modpackName or DEFAULT_NAME,
        "summary": summary or DEFAULT_SUMMARY,
        "files": [],
        "dependencies": {
            "minecraft": minecraftVersion or None,
            "fabric-loader": fabricLoaderVersion or None
        }
    }

    copyFilesThreaded('config', addConfig, folder)
    addFilesThreaded('mods', addMods, folder, forced, defaultIndex)
    addFilesThreaded('resourcepacks', addResourcepacks, folder, forced, defaultIndex)
    addFilesThreaded('shaderpacks', addShaderpacks, folder, forced, defaultIndex)

    with (TMP_FOLDER / 'modrinth.index.json').open('w') as f:
        dump(defaultIndex, f, indent=4)

    deleteEmptyFolders(TMP_FOLDER)
    outputFolder = outputFolder or DEFAULT_OUTPUT_FOLDER
    outputFolder.mkdir(parents=True, exist_ok=True)
    mrpackFile = outputFolder / 'output.mrpack'
    createMrpack(TMP_FOLDER, mrpackFile)
    rmtree(TMP_FOLDER)

def downloadAndVerify(fileInfo: Dict, minecraftFolder: Path, skipHash: bool):
    """Downloads and verifies a file based on the information provided.
    
    Args:
        fileInfo (Dict): A dictionary containing file information.
        minecraftFolder (Path): The path to the .minecraft folder.
        skipHash (bool): Whether to skip hash verification.
    """
    filePath = minecraftFolder / fileInfo['path']
    filePath.parent.mkdir(parents=True, exist_ok=True)

    for downloadUrl in fileInfo['downloads']:
        if downloadFile(downloadUrl, filePath, fileInfo['hashes']['sha1'], skipHash):
            print(GREEN.format(f"File {filePath.name} downloaded and verified successfully."))
            break
        else:
            print(RED.format(f"Hash mismatch for {filePath.name}. Trying the next download URL."))
            filePath.unlink()


def downloadFile(url: str, filePath: Path, expectedHash: str, skipHash: bool = False) -> bool:
    """Downloads a file from a URL and verifies its hash.

    Args:
        url (str): The download URL.
        filePath (Path): The path to save the file.
        expectedHash (str): The expected SHA-1 hash of the file.
        skipHash (bool): Whether to skip hash verification.

    Returns:
        bool: True if the file was downloaded and verified successfully, False otherwise.
    """
    try:
        response = _get(url, stream=True, headers=getUA())
        response.raise_for_status()

        with filePath.open('wb') as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                file.write(chunk)

        if skipHash:
            print(GREEN.format(f"Downloaded {filePath.name} without hash verification"))
            return True

        fileHash = sha1(filePath.read_bytes()).hexdigest()
        if fileHash == expectedHash:
            print(GREEN.format(f"Downloaded and verified {filePath.name} successfully"))
            return True
        else:
            print(RED.format(f"Hash mismatch for {filePath.name}: expected {expectedHash}, got {fileHash}"))
            return False
    except requestsExceptions.RequestException as e:
        print(RED.format(f"Error downloading {filePath.name}: {e}"))
        return False


def getArchive(fp: Path, outputPath: Optional[Path] = None, skipHash: bool = False):
    """Extracts and downloads the contents of a modpack archive (.mrpack).

    Args:
        fp (Path): The path to the modpack archive.
        outputPath (Optional[Path]): The output path for the extracted files.
        skipHash (bool): Whether to skip hash verification.
    """
    with ZipFile(fp, 'r') as archive:
        with archive.open('modrinth.index.json') as indexFile:
            indexData = load(indexFile)

    TMP_FOLDER.mkdir(exist_ok=True)
    resultsFolder = outputPath or DEFAULT_OUTPUT_FOLDER
    minecraftFolder = resultsFolder / '.minecraft'
    minecraftFolder.mkdir(parents=True, exist_ok=True)

    print(GREEN.format(f"Created Minecraft folder at: {minecraftFolder}"))

    with ZipFile(fp, 'r') as archive:
        for item in archive.infolist():
            # Check if '/' exists in the filename before splitting
            if '/' in item.filename:
                targetPath = minecraftFolder / item.filename.split('/', 1)[1]
                if item.is_dir():
                    targetPath.mkdir(parents=True, exist_ok=True)
                else:
                    targetPath.parent.mkdir(parents=True, exist_ok=True)
                    with targetPath.open('wb') as targetFile, archive.open(item.filename) as sourceFile:
                        targetFile.write(sourceFile.read())

    print(GREEN.format(f"Extracted files to: {minecraftFolder}"))

    with ThreadPoolExecutor() as executor:
        executor.map(lambda fileInfo: downloadAndVerify(fileInfo, minecraftFolder, skipHash), indexData['files'])

    if (TMP_FOLDER / '.minecraft').exists():
        move(str(TMP_FOLDER / '.minecraft'), str(resultsFolder))
        print(GREEN.format(f"Moved .minecraft to {resultsFolder}"))
    else:
        print(RED.format(f"Directory {TMP_FOLDER / '.minecraft'} does not exist. Skipping move operation."))

    rmtree(TMP_FOLDER, ignore_errors=True)


def main():
    parser = ArgumentParser(description="Create or extract Minecraft modpack archives.")
    parser.add_argument('-i', '--input', required=True, help="Input file path")
    parser.add_argument('-g', '--get', action='store_true', help="Extract modpack archive")
    parser.add_argument('-c', '--create', action='store_true', help="Create modpack archive")
    parser.add_argument('-o', '--output', help="Output file path")
    parser.add_argument('-fo', '--force-override', action='store_true', help="Force override files without prompting")
    parser.add_argument('-sh', '--skip-hash', action='store_true', help="Skip hash verification")

    args = parser.parse_args()

    inputPath = Path(args.input)
    outputPath = Path(args.output) if args.output else None

    if args.get:
        getArchive(inputPath, outputPath, args.skip_hash)
    elif args.create:
        createArchive(
            folder=inputPath,
            forced=args.force_override,
            outputFolder=outputPath
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    cls()
    main()
