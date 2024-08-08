#!/usr/bin/env python3
global DEBUG

DEBUG = True

import os
import sys
import stat
import subprocess
import glob
import uuid
from pathlib import Path  # core python module


# getting the name of the directory
# where the this file is present.
current = os.path.dirname(os.path.realpath(__file__))

# Getting the parent directory name
# where the current directory is present.
parent = os.path.dirname(current)

# adding the parent directory to
# the sys.path.
sys.path.append(parent)
imgdir = os.path.join(parent, "resources", "images")

# Check if python 3.11 or later is available and running
from src.VersionCheck import version_check

version_check()

from src.Utils import *  # copy_to_clipboard comes from Utils

# import pysimplegui
import PySimpleGUI as sg

global XAVIERDIR
global SIFCACHE
global XAVIER
global XAVIERVER
global RANDOMSTR
global FILES2DELETE
global HOSTNAME

XAVIERDIR = os.getenv("XAVIERDIR")
SIFCACHE = os.getenv("SIFCACHE")
XAVIERVER = os.getenv("XAVIERVER")
HOSTNAME = os.getenv("HOSTNAME")
XAVIER = os.path.join(XAVIERDIR, XAVIERVER, "bin", "xavier")
RANDOMSTR = str(uuid.uuid4())
FILES2DELETE = list()

# sg.SetOptions(button_color=sg.COLOR_SYSTEM_DEFAULT)


def get_combos():
    config_dir = os.path.join(XAVIERDIR, XAVIERVER, "config")
    if not os.path.exists(config_dir):
        sys.exit("ERROR: Folder does not exist : {}".format(config_dir))
    if HOSTNAME == "biowulf.nih.gov":
        cluster = "biowulf"
    elif HOSTNAME == "fsitgl-head01p.ncifcrf.gov":
        cluster = "frce"
    else:
        sys.exit("ERROR: XAVIER GUI only works on Biowulf or FRCE clusters")
    searchterm = config_dir + "/genomes/*" + cluster + ".json"
    jsonfiles = glob.glob(searchterm)
    if len(jsonfiles) == 0:
        sys.exit("ERROR: No Genome JSONs found in : {}".format(config_dir))
    jsons = dict()
    for j in jsonfiles:
        k = os.path.basename(j)
        k = k.replace("." + cluster + ".json", "")
        jsons[k] = j
    return jsons


def fixpath(p):
    return os.path.abspath(os.path.expanduser(p))


def get_fastqs(inputdir):
    inputdir = fixpath(inputdir)
    inputfastqs = glob.glob(inputdir + os.sep + "*.fastq.gz")
    inputfqs = glob.glob(inputdir + os.sep + "*.fq.gz")
    inputfastqs.extend(inputfqs)
    return inputfastqs


def deletefiles():
    for f in FILES2DELETE:
        os.remove(f)


def run(cmd, init=False, dry=False, run=False):
    if init:
        cmd += " --runmode init"
    if dry:
        cmd += " --runmode dryrun"
    if run:
        cmd += " --runmode run"
    runner_file = os.path.join(os.getenv("HOME"), RANDOMSTR + ".xavier.runner")
    with open(runner_file, "w") as runner:
        runner.write(cmd)
    st = os.stat(runner_file)
    os.chmod(runner_file, st.st_mode | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    x = subprocess.run(runner_file, capture_output=True, shell=True, text=True)
    run_stdout = x.stdout.encode().decode("utf-8")
    run_stderr = x.stderr.encode().decode("utf-8")
    return run_stdout, run_stderr


def main():
    # get drop down genome options
    jsons = get_combos()
    genome_annotation_combinations = list(jsons.keys())
    genome_annotation_combinations.sort()
    if DEBUG:
        print(jsons)
    if DEBUG:
        print(genome_annotation_combinations)

    # Create different layouts
    tumorPair_layout = [
        [
            sg.Text("Pairs file", size=(20, 1)),
            sg.InputText(key="-PAIRS-"),
            sg.FileBrowse(target="-PAIRS-"),
        ],
        [
            sg.Text("Copy Number Variants (CNV):"),
            sg.Radio("No", "CNVRADIO", enable_events=True, default=True, key="-NOCNV-"),
            sg.Radio("Yes", "CNVRADIO", enable_events=True, key="-CNV-"),
        ],
    ]

    tumorOnly_layout = [
        [sg.T("Copy Number Variants (CNVs) can only be analyzed in Tumor-Normal mode.")]
    ]

    analysis_layout = [
        [
            sg.Radio(
                "Tumor-normal pair", "TUMORADIO", enable_events=True, key="-TUMNORM-"
            ),
            sg.Radio("Tumor-only", "TUMORADIO", enable_events=True, key="-TUMONLY-"),
        ],
        [
            sg.Frame(
                "Tumor-Normal",
                tumorPair_layout,
                font=("Helvetica", 12, "bold"),
                key="-PAIROPTS-",
                visible=False,
            )
        ],
        [
            sg.Frame(
                "Tumor-Only",
                tumorOnly_layout,
                font=("Helvetica", 12, "bold"),
                key="-ONLYOPTS-",
                visible=False,
            )
        ],
    ]

    targets_layout = [
        [
            sg.Text("Targets .BED file", size=(20, 1)),
            sg.InputText(key="-TARGETS-"),
            sg.FileBrowse(target="-TARGETS-"),
        ]
    ]

    settings_layout = [
        [sg.T("Please read the Documentation before changing")],
        [
            sg.T("Apply FFPE correction?"),
            sg.Radio(
                "No", "FFPERADIO", enable_events=True, default=True, key="-NOFFPE-"
            ),
            sg.Radio("Yes", "FFPERADIO", enable_events=True, key="-FFPE-"),
        ],
        [sg.T("Targets (.BED file):")],
        [
            sg.Radio(
                "Default", "BEDRADIO", enable_events=True, default=True, key="-DEFTARG-"
            ),
            sg.Radio("Custom", "BEDRADIO", enable_events=True, key="-CUSTARG-"),
        ],
        [sg.Frame("Custom Targets", targets_layout, visible=False, key="-BED-")],
        [sg.Button(button_text="Discard", key="-DISCSET-", button_color="#3864AB")],
    ]

    default_values = {
        "-NOCNV-": True,
        "-CNV-": False,
        "-NOFFPE-": True,
        "-FFPE-": False,
        "-DEFTARG-": True,
        "-CUSTARG-": False,
    }
    textKeys = [
        "-INDIR-",
        "-OUTDIR-",
        "-PAIRS-",
        "-TARGETS-",
        "-JOBNAME-",
        "-ANNOTATION-",
    ]
    # create main layout
    logo = sg.Image(os.path.join(imgdir, "CCBRlogo.png"))
    layout = [
        [sg.Column([[logo]], justification="center")],
        [
            sg.Text(
                "XAVIER - eXome Analysis and Variant explorER",
                font=("Helvetica", 12, "bold"),
            )
        ],
        [
            sg.Text("Input Fastqs folder", size=(20, 1)),
            sg.InputText(key="-INDIR-"),
            sg.FolderBrowse(target="-INDIR-"),
        ],
        [
            sg.Text("Output folder", size=(20, 1)),
            sg.InputText(key="-OUTDIR-"),
            sg.FolderBrowse(target="-OUTDIR-"),
        ],
        [
            sg.Text("Genome", size=(20, 1)),
            sg.Combo(
                values=genome_annotation_combinations,
                key="-ANNOTATION-",
                tooltip="hg38: Homo sapiens GRCh38.p14; mm10: Mus musculus GRCm38.p6",
            ),
        ],
        [
            sg.Text("Job name", size=(20, 1)),
            sg.InputText(
                key="-JOBNAME-",
                tooltip="Name of the job for this run. All output files will be stored under this folder name in the output folder.",
            ),
        ],
        [sg.Frame("Analysis Mode", analysis_layout, visible=True)],
        [sg.Button(button_text="Additional Settings", key="-SETTINGS-")],
        [sg.Frame("", settings_layout, key="-SET-", visible=False)],
        [
            sg.Submit(key="-SUBMIT-"),
            sg.Button(button_text="Documentation", key="--DOC--"),
            sg.Button(button_text="Help", key="--HELP--"),
            sg.Cancel(key="--CANCEL--", button_color="tomato"),
        ],
    ]

    if DEBUG:
        print("layout is ready!")

    window = sg.Window("XAVIER " + XAVIERVER, layout, location=(0, 500), finalize=True)
    if DEBUG:
        print("window created!")

    # Event loop:
    while True:
        event, values = window.read()
        # if DEBUG: print(event,values) ## Turn on for debugging

        # if any((event != 'Submit')):
        if event in ("--CANCEL--", sg.WINDOW_CLOSED):
            sg.popup_auto_close(
                "Thank you for running XAVIER. GoodBye!", location=(0, 500), title=""
            )
            sys.exit(69)
        if event == "-TUMNORM-":
            window["-PAIROPTS-"].update(visible=True)
            window["-ONLYOPTS-"].update(visible=False)
        elif event == "-TUMONLY-":
            window["-PAIROPTS-"].update(visible=False)
            window["-ONLYOPTS-"].update(visible=True)
            values["-CNV-"] = False
        if event == "--DOC--":
            copy_to_clipboard("https://ccbr.github.io/XAVIER/")
            sg.Popup(
                "Visit https://ccbr.github.io/XAVIER/ for links to complete documentation. The link has been copied to your clipboard. Please paste it in your favorite web browser.",
                font=("Arial", 12, "bold"),
                title="",
                location=(0, 500),
            )
            continue
        if event == "--HELP--":
            copy_to_clipboard("ccbr_pipeliner@mail.nih.gov")
            sg.Popup(
                "Email ccbr_pipeliner@mail.nih.gov for help. The email id has been copied to your clipboard. Please paste it in your emailing software.",
                font=("Arial", 12, "bold"),
                title="",
                location=(0, 500),
            )
            continue
        if event == "-SETTINGS-":
            window["-SET-"].update(visible=True)
        if event == "-DEFTARG-":
            window["-BED-"].update(visible=False)
        if event == "-CUSTARG-":
            window["-BED-"].update(visible=True)
            targets_file = values["-TARGETS-"]
        if event == "-DISCSET-":
            window["-SET-"].update(visible=False)
            window["-BED-"].update(visible=False)
            for key, value in default_values.items():
                window[key].Update(value)
        if event == "-SUBMIT-":
            # check for correct inputs
            if values["-INDIR-"] == "":
                sg.PopupError("Input folder must be provided!!", location=(0, 500))
                continue
            elif not os.path.exists(values["-INDIR-"]):
                sg.PopupError("Input folder doesn't exist!!", location=(0, 500))
                continue
            elif len(get_fastqs(values["-INDIR-"])) == 0:
                sg.PopupError("Input folder has no fastqs!!", location=(0, 500))
                continue
            else:
                inputfastqs = get_fastqs(values["-INDIR-"])
                if DEBUG:
                    print(inputfastqs)
                if len(inputfastqs) == 0:
                    sg.PopupError(
                        "Input folder has no fastqs!!",
                        location=(0, 500),
                        title="ERROR!",
                        font=("Arial", 12, "bold"),
                    )
                    window.Element("-INDIR-").update("")
                    continue
            if values["-OUTDIR-"] == "":
                sg.PopupError("Output folder must be provided!!", location=(0, 500))
                continue
            outputfolder = values["-OUTDIR-"] + "/" + values["-JOBNAME-"]
            if os.path.exists(outputfolder):
                ch = sg.popup_yes_no(
                    "Output folder name exists... this is probably a re-run ... proceed?",
                    title="Rerun??",
                    location=(0, 500),
                )
                if ch == "No":
                    window.Element("-OUTDIR-").update("")
                    continue
            if values["-CUSTARG-"] == True:
                if values["-TARGETS-"] == "":
                    sg.PopupError(
                        "Custom Targets BED file selected but not provided!!",
                        location=(0, 500),
                    )
                    continue
                else:
                    targets_file = values["-TARGETS-"]
            if values["-TUMNORM-"] == "" and values["-TUMONLY-"] == "":
                sg.PopupError("Select an analysis mode", location=(0, 500))
                continue
            if values["-TUMNORM-"] == True:
                if values["-PAIRS-"] == "":
                    sg.PopupError(
                        "Tumor-normal mode selected. Need Pairs file to continue",
                        location=(0, 500),
                    )
                    continue
                else:
                    pairs_file = values["-PAIRS-"]

            genome = values["-ANNOTATION-"]
            targets_file = (
                os.path.join(XAVIERDIR, XAVIERVER, "resources")
                + "/*"
                + genome
                + "*.bed"
            )

            xavier_cmd = XAVIER + " run "
            xavier_cmd += " --input " + values["-INDIR-"] + "/*.R?.fastq.gz"
            xavier_cmd += " --output " + values["-OUTDIR-"] + "/" + values["-JOBNAME-"]
            xavier_cmd += " --genome " + genome
            xavier_cmd += " --targets " + targets_file
            xavier_cmd += " --mode slurm "

            if HOSTNAME == "fsitgl-head01p.ncifcrf.gov":
                xavier_cmd += " --sif-cache " + SIFCACHE + "/XAVIER"
                xavier_cmd += " --tmp-dir /scratch/cluster_scratch/$USER/"

            if values["-TUMNORM-"] == True:
                xavier_cmd += " --pairs " + pairs_file
                if values["-CNV-"] == True:
                    xavier_cmd += " --cnv "

            if values["-FFPE-"] == True:
                xavier_cmd += " --ffpe "

            run_stdout, run_stderr = run(xavier_cmd, init=True, dry=False, run=False)
            run_stdout, run_stderr = run(xavier_cmd, init=False, dry=True, run=False)
            if DEBUG:
                print(run_stdout)
            if DEBUG:
                print(run_stderr)
            allout = "{}\n{}".format(run_stdout, run_stderr)
            sg.popup_scrolled(
                allout, title="Dryrun:STDOUT/STDERR", location=(0, 500), size=(80, 30)
            )
            if "error" in allout or "Error" in allout or "ERROR" in allout:
                continue
            ch = sg.popup_yes_no(
                "Submit run to slurm?", title="Submit??", location=(0, 500)
            )
            if ch == "Yes":
                run_stdout, run_stderr = run(
                    xavier_cmd, init=False, dry=False, run=True
                )
                if DEBUG:
                    print(run_stdout)
                if DEBUG:
                    print(run_stderr)
                allout = "{}\n{}".format(run_stdout, run_stderr)
                sg.popup_scrolled(
                    allout,
                    title="Slurmrun:STDOUT/STDERR",
                    location=(0, 500),
                    size=(80, 30),
                )
                runner_file = os.path.join(
                    os.getenv("HOME"), RANDOMSTR + ".xavier.runner"
                )
                FILES2DELETE.append(runner_file)
                rerun = sg.popup_yes_no(
                    "Submit another XAVIER job?", title="", location=(0, 500)
                )
                if rerun == "Yes":
                    for key in window.read():
                        window[key].Update(value="")
                        window["-PAIROPTS-"].update(visible=False)
                        window["-ONLYOPTS-"].update(visible=False)
                        window["-TUMNORM-"].update(value=False)
                        window["-TUMONLY-"].update(value=False)
                if rerun == "No":
                    sg.popup_auto_close(
                        "Thank you for running XAVIER. GoodBye!",
                        location=(0, 500),
                        title="",
                    )
                    break
            elif ch == "No":
                for key in textKeys:
                    window[key].Update(value="")
                for key, value in default_values.items():
                    window[key].Update(value)
                window["-PAIROPTS-"].update(visible=False)
                window["-ONLYOPTS-"].update(visible=False)
                window["-TUMNORM-"].update(value=False)
                window["-TUMONLY-"].update(value=False)
                continue

    window.close()
    if len(FILES2DELETE) != 0:
        deletefiles()


# $ ./exome-seek run [--help] \
#                   [--mode {local, slurm}] \
#                   [--job-name JOB_NAME] \
#                   [--callers {mutect2,mutect,strelka, ...}] \
#                   [--pairs PAIRS] \
#                   [--ffpe] \
#                   [--cnv] \
#                   [--silent] \
#                   [--singularity-cache SINGULARITY_CACHE] \
#                   [--sif-cache SIF_CACHE] \
#                   [--threads THREADS] \
#                   --runmode {init, dryrun, run} \
#                   --input INPUT [INPUT ...] \
#                   --output OUTPUT \
#                   --genome {hg38, ...} \
#                   --targets TARGETS


if __name__ == "__main__":
    main()