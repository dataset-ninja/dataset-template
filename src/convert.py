# Path to the original dataset
import os
import supervisely as sly
import gdown
import src.settings as s
from dataset_tools.convert import unpack_if_archive

def download_dataset():
    archive_path = sly.app.get_data_dir()

    if not os.path.exists(archive_path):
        if isinstance(s.DOWNLOAD_ORIGINAL_URL, str):
            gdown.download(s.DOWNLOAD_ORIGINAL_URL, archive_path, quiet=False)
        if isinstance(s.DOWNLOAD_ORIGINAL_URL, dict):
            for name, url in s.DOWNLOAD_ORIGINAL_URL:
                gdown.download(url, os.path.join(archive_path, name), quiet=False)
    else:
        sly.logger.info(f"Path '{archive_path}' already exists.")
    return unpack_if_archive(archive_path)    


def convert_and_upload_supervisely_project(
    api: sly.Api, workspace_id: int, project_name: str
) -> sly.ProjectInfo:

    # * dataset_path = download_dataset()

    # Function should read local dataset and upload it to Supervisely project, then return project info.

    raise NotImplementedError("The converter should be implemented manually.")

    # * return project
