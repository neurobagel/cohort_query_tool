"""CRUD functions called by path operations."""
import os

import httpx
import pandas as pd
from fastapi import HTTPException

from . import utility as util
from .models import AggDatasetResponse


async def get(
    age_min: float,
    age_max: float,
    sex: str,
    diagnosis: str,
    is_control: bool,
    min_num_sessions: int,
    image_modal: str,
    assessment: str,
):
    """
    Makes a POST request to Stardog API using httpx where the payload is a SPARQL query generated by the create_query function.

    Parameters
    ----------
    age_min : float
        Minimum age of subject.
    age_max : float
        Maximum age of subject.
    sex : str
        Sex of subject.
    diagnosis : str
        Subject diagnosis.
    is_control : bool
        Whether or not subject is a control.
    min_num_sessions : int
        Subject minimum number of imaging sessions.
    image_modal : str
        Imaging modality of subject scans.
    assessment : str
        Non-imaging assessment completed by subjects.

    Returns
    -------
    httpx.response
        Response of the POST request.

    """
    response = httpx.post(
        url=util.QUERY_URL,
        content=util.create_query(
            age=(age_min, age_max),
            sex=sex,
            diagnosis=diagnosis,
            is_control=is_control,
            min_num_sessions=min_num_sessions,
            image_modal=image_modal,
            assessment=assessment,
        ),
        headers=util.QUERY_HEADER,
        auth=httpx.BasicAuth(
            os.environ.get("USER"), os.environ.get("PASSWORD")
        ),
    )

    if not response.is_success:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"{response.reason_phrase}: {response.text}",
        )

    results = response.json()

    results_dicts = [
        {k: v["value"] for k, v in res.items()}
        for res in results["results"]["bindings"]
    ]
    results_df = pd.DataFrame(results_dicts)

    response_obj = []
    if not results_df.empty:
        for (dataset, dataset_name), group in results_df.groupby(
            by=["dataset", "dataset_name"]
        ):
            response_obj.append(
                AggDatasetResponse(
                    dataset=dataset,
                    dataset_name=dataset_name,
                    num_matching_subjects=group.shape[0],
                )
            )

    return response_obj
