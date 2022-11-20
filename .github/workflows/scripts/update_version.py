import argparse
import os
import json
import re


def collapse_json(text, list_length=4):
    for length in range(list_length):
        re_pattern = r'\[' + (r'\s*(.+)\s*,' * length)[:-1] + r'\]'
        re_repl = r'[' + ''.join(r'\{}, '.format(i+1) for i in range(length))[:-2] + r']'

        text = re.sub(re_pattern, re_repl, text)

    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    def parse_list(text):
        return text.split(",")
    parser.add_argument("-files", type=parse_list, default=[], nargs='?', const=[])
    parser.add_argument("-removed", type=parse_list, default=[], nargs='?', const=[])
    args = parser.parse_args()

    addon_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    version = (0, 0, 0)
    with open(os.path.join(addon_directory, "ActRec/__init__.py"), 'r', encoding='utf-8') as file:
        for line in file.readlines():
            if "version" in line:
                version = eval("%s)" % line.split(":")[1].split(")")[0].strip())
                break
    with open(os.path.join(addon_directory, "ActRec/actrec/config.py"), 'r', encoding='utf-8') as file:
        for line in file.readlines():
            if "version" in line:
                check_version = eval(line.split("=")[1].strip())
                if check_version > version:
                    version = check_version
                break

    print("Update to Version %s\nFiles: %s\nRemoved: %s" % (version, args.files, args.removed))

    version = list(version)
    with open(os.path.join(addon_directory, "download_file.json"), 'r', encoding='utf-8') as download_file:
        data = json.loads(download_file.read())
        data_files = data["files"]
        for file in args.files:
            if data_files.get(file, None):
                data_files[file] = version
        data_remove = data["remove"]
        for file in args.removed:
            if file not in data_remove:
                data_remove.append(file)
        data["version"] = version
    with open(os.path.join(addon_directory, "download_file.json"), 'w', encoding='utf-8') as download_file:
        download_file.write(collapse_json(json.dumps(data, ensure_ascii=False, indent=4)))

    lines = []
    with open(os.path.join(addon_directory, "ActRec/__init__.py"), 'r', encoding='utf-8') as file:
        for line in file.read().splitlines():
            if "version" in line:
                split = line.split(": ")
                sub_split = split[1].split(")")
                line = "%s: %s%s" % (split[0], str(tuple(version)), sub_split[-1])
            lines.append(line)
    with open(os.path.join(addon_directory, "ActRec/__init__.py"), 'w', encoding='utf-8') as file:
        file.write("\n".join(lines))
        file.write("\n")

    lines = []
    with open(os.path.join(addon_directory, "ActRec/actrec/config.py"), 'r', encoding='utf-8') as file:
        for line in file.read().splitlines():
            if "version" in line:
                split = line.split("=")
                line = "version = %s" % str(tuple(version))
            lines.append(line)
    with open(os.path.join(addon_directory, "ActRec/actrec/config.py"), 'w', encoding='utf-8') as file:
        file.write("\n".join(lines))
        file.write("\n")
