import json
import os
import sys

import dataset_tools as dtools
import supervisely as sly
from dotenv import load_dotenv

from src.convert import convert_and_upload_supervisely_project

# !    Checklist before running the app:
# * 1. Set project name and project name full.
# * 2. Prepare convert_and_upload_supervisely_project() function in convert.py
#      It should receive API object, workspace_id and project_name and return project_info of the created project.
# * 3. Fill out neccessary fields in custom data dict.
# * 4. Launch the script.
# ? 5. Fill out CITATION.md, EXPERT.md, LICENSE.md, README.md
# ? 6. Push to GitHub.

# Names of the project that will appear on instance and on Ninja webpage.
PROJECT_NAME = "basic name (short)"
PROJECT_NAME_FULL = "full name (long)" 
DOWNLOAD_ORIGINAL_URL = "https://some.com/dataset/dowload_url"  # Union[None, str]


# Create instance of supervisely API object.
load_dotenv(os.path.expanduser("~/ninja.env"))
load_dotenv("local.env")
api = sly.Api.from_env()
team_id = sly.env.team_id()
workspace_id = sly.env.workspace_id()
server_address = os.getenv("SERVER_ADDRESS")
sly.logger.info(
    f"Connected to Supervisely. Server address: {server_address}, team_id: {team_id}, workspace_id: {workspace_id}."
)

# Create directories for result stats and visualizations.
os.makedirs("./stats/", exist_ok=True)
os.makedirs("./visualizations/", exist_ok=True)

# Trying to retreive project info from instance by name.
project_info = api.project.get_info_by_name(workspace_id, PROJECT_NAME)
if not project_info:
    # If project doesn't found on instance, create it and use new project info.
    project_info = convert_and_upload_supervisely_project(api, workspace_id, PROJECT_NAME)
    sly.logger.info(f"Project {PROJECT_NAME} not found on instance. Created new project.")
    sly.logger.info(f"Now you can explore created project and choose 'preview_image_id'.")
    sys.exit(0)
else:
    sly.logger.info(f"Found project {PROJECT_NAME} on instance, will use it.")

project_id = project_info.id

# How the app will work: from instance or from local directory.
from_instance = True  # ToDo: Automatically detect if app is running from instance or locally.

# * Step 1: Read project and project meta
# ? Option 1: From supervisely instance

if from_instance:
    sly.logger.info("The app in the instance mode. Will download data from Supervisely.")

    project_meta = sly.ProjectMeta.from_json(api.project.get_meta(project_id))
    datasets = api.dataset.get_list(project_id)

    sly.logger.info(
        f"Prepared project meta and read {len(datasets)} datasets for project with id={project_id}."
    )

# ? Option 2: From local directory
# ! Not implemented yet
# project_path = os.environ["LOCAL_DATA_DIR"]
# sly.download(api, project_id, project_path, save_image_info=True, save_images=False)
# project_meta = sly.Project(project_path, sly.OpenMode.READ).meta
# datasets = None

# * Step 2: Get download link
download_sly_url = dtools.prepare_download_link(project_info)
dtools.update_sly_url_dict(
    {
        PROJECT_NAME: {
            "id": project_id,
            "download_sly_url": download_sly_url,
            "download_original_url": DOWNLOAD_ORIGINAL_URL,
        }
    }
)
sly.logger.info(f"Prepared download link: {download_sly_url}")


# * Step 3: Update project custom data
sly.logger.info("Updating project custom data...")
custom_data = {
    #####################
    # ! required fields #
    #####################
    "name": PROJECT_NAME,  # * Should be filled in the beginning of file
    "fullname": PROJECT_NAME_FULL,  # * Should be filled in the beginning of file
    "cv_tasks": ["semantic segmentation", "object detection", "instance segmentation"], 
    "annotation_types": ["instance segmentation"], 
    "industries": ["general domain"],
    "release_year": 2018, 
    "homepage_url": "https://www.kaggle.com/datasets/kumaresanmanickavelu/lyft-udacity-challenge", 
    "license": "CC0: Public Domain", 
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/", 
    "preview_image_id": 224318,  # This should be filled AFTER uploading images to instance, just ID of any image
    "github_url": "https://github.com/dataset-ninja/synthetic-plants",  # input url to GitHub repo in dataset-ninja
    "github": "dataset-ninja/synthetic-plants",  # input GitHub repo in dataset-ninja (short way)
    "download_sly_url": download_sly_url,
    #####################
    # ? optional fields #
    #####################
    # "download_original_url": DOWNLOAD_ORIGINAL_URL # Union[None, str],
    # "paper": Union[None, str],
    # "citation_url": None,  # FILL IT!
    # "organization_name": Union[None, str, list],
    # "organization_url": Union[None, str, list],
    # "tags": [],
}

# * Update custom data and retrieve updated project info and custom data from instance.
api.project.update_custom_data(project_id, custom_data)
project_info = api.project.get_info_by_id(project_id)
custom_data = project_info.custom_data
sly.logger.info("Successfully updated project custom data.")


def build_stats():
    sly.logger.info("Starting to build stats...")

    stats = [
        dtools.ClassBalance(project_meta),
        dtools.ClassCooccurrence(project_meta, force=False),
        dtools.ClassesPerImage(project_meta, datasets),
        dtools.ObjectsDistribution(project_meta),
        dtools.ObjectSizes(project_meta),
        dtools.ClassSizes(project_meta),
    ]
    heatmaps = dtools.ClassesHeatmaps(project_meta)
    classes_previews = dtools.ClassesPreview(project_meta, project_info.name, force=False)
    previews = dtools.Previews(project_id, project_meta, api, team_id)

    for stat in stats:
        if not sly.fs.file_exists(f"./stats/{stat.basename_stem}.json"):
            stat.force = True
    stats = [stat for stat in stats if stat.force]

    if not sly.fs.file_exists(f"./stats/{heatmaps.basename_stem}.png"):
        heatmaps.force = True
    if not sly.fs.file_exists(f"./visualizations/{classes_previews.basename_stem}.webm"):
        classes_previews.force = True
    if not api.file.dir_exists(team_id, f"/dataset/{project_id}/renders/"):
        previews.force = True
    vstats = [stat for stat in [heatmaps, classes_previews, previews] if stat.force]

    dtools.count_stats(
        project_id,
        stats=stats + vstats,
        sample_rate=1,
    )

    sly.logger.info("Saving stats...")
    for stat in stats:
        with open(f"./stats/{stat.basename_stem}.json", "w") as f:
            json.dump(stat.to_json(), f)
        stat.to_image(f"./stats/{stat.basename_stem}.png")

    if len(vstats) > 0:
        if heatmaps.force:
            heatmaps.to_image(f"./stats/{heatmaps.basename_stem}.png", draw_style="outside_black")
        if classes_previews.force:
            classes_previews.animate(f"./visualizations/{classes_previews.basename_stem}.webm")
        if previews.force:
            previews.close()

    sly.logger.info("Successfully built and saved stats.")


def build_visualizations():
    sly.logger.info("Starting to build visualizations...")

    renderers = [
        dtools.Poster(project_id, project_meta, force=False),
        dtools.SideAnnotationsGrid(project_id, project_meta),
    ]
    animators = [
        dtools.HorizontalGrid(project_id, project_meta),
        dtools.VerticalGrid(project_id, project_meta, force=False),
    ]

    for vis in renderers + animators:
        if not sly.fs.file_exists(f"./visualizations/{vis.basename_stem}.png"):
            vis.force = True
    renderers, animators = [r for r in renderers if r.force], [a for a in animators if a.force]

    for a in animators:
        if not sly.fs.file_exists(f"./visualizations/{a.basename_stem}.webm"):
            a.force = True
    animators = [a for a in animators if a.force]

    # ? Download fonts from: https://fonts.google.com/specimen/Fira+Sans
    dtools.prepare_renders(
        project_id,
        renderers=renderers + animators,
        sample_cnt=40,
    )

    sly.logger.info("Saving visualizations...")

    for vis in renderers + animators:
        vis.to_image(f"./visualizations/{vis.basename_stem}.png")
    for a in animators:
        a.animate(f"./visualizations/{a.basename_stem}.webm")

    sly.logger.info("Successfully built and saved visualizations.")


def build_summary():
    sly.logger.info("Starting to build summary...")

    summary_data = dtools.get_summary_data_sly(project_info)

    classes_preview = None
    if sly.fs.file_exists("./visualizations/classes_preview.webm"):
        classes_preview = (
            f"{custom_data['github_url']}/raw/main/visualizations/classes_preview.webm"
        )

    summary_content = dtools.generate_summary_content(
        summary_data,
        vis_url=classes_preview,
    )

    with open("SUMMARY.md", "w") as summary_file:
        summary_file.write(summary_content)

    sly.logger.info("Successfully built and saved summary.")


def main():
    pass

    sly.logger.info("Script is starting...")

    build_stats()
    build_visualizations()
    build_summary()

    sly.logger.info("Script finished successfully.")


if __name__ == "__main__":
    main()
