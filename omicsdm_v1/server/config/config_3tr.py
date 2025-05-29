class GeneralConfig:
    """
    This is a config file specific for the columns etc
    of the 3TR project. It contains no secret keys/passwords
    and is therefore under version control.
    """

    # Templates for dataset creation and file submission
    TEMPLATE_FOLDER = "templates/"

    DATASET_EXAMPLE = (
        [
            "Dataset ID",
            "Dataset Name",
            "Dataset Description",
            "Responsible Partner",
            "Disease",
            "Treatment",
            "Category",
            "Tags",
            "Visibility",
        ],
        [
            "test",
            "our first dataset",
            "Lorem ipsum dolor",
            "CNAG,CRG",
            "ASTHMA",
            "Drug X",
            "Microbiome",
            "ASTHMA,Drug X",
            "private",
        ],
        [
            "test2",
            "our second dataset",
            "Lorem ipsum dolor",
            "CNAG,CRG",
            "COPD",
            "None",
            "Imaging and histology/pathology",
            "COPD",
            "private",
        ],
    )

    FILE_EXAMPLE = (
        ["Dataset ID", "Platform", "Comment"],
        [
            "test",
            "LC-MS",
            "Hello",
        ],
        [
            "test2",
            "WGBS",
            "World",
        ],
    )

    # Submission (Dataset creation/ File upload/ Analysis Submission)
    general_fields = [
        "id",
        "name",
        "description",
        "tags",
        "visibility",
    ]  # types = string

    # Dataset submission
    DATASET_FIELDS = general_fields + [
        "responsible_partner",
        "disease",
        "treatment",
        "category",
    ]  # types = string

    DATASET_FIELDS = [
        "id",
        "project_id",
        "name",
        "disease",
        "treatment",
        "molecularInfo",
        "sampleType",
        "dataType",
        "valueType",
        "platform",
        "genomeAssembly",
        "annotation",
        "samplesCount",
        "featuresCount",
        "featuresID",
        "healthyControllsIncluded",
        "additionalInfo",
        "contact",
        "tags",
        "visibility",
        "submitter_name",
        "submit_date",
        "shared_with",
    ]

    # for dataset submission
    DATASET_FIELDS_TO_TYPES = {
        "id": "string",
        "project_id": "string",
        "name": "string",
        "disease": "string",
        "treatment": "string",
        "molecularInfo": "string",
        "sampleType": "string",
        "dataType": "string",
        "valueType": "string",
        "platform": "string",
        "genomeAssembly": "string",
        "annotation": "string",
        "samplesCount": "integer",
        "featuresCount": "integer",
        "featuresID": "string",
        "healthyControllsIncluded": "boolean",
        "additionalInfo": "string",
        "contact": "string",
        "tags": "string",
        "visibility": "string",
        "submitter_name": "string",
        "submit_date": "string",
        "shared_with": "string",
        "file": "array",
        "file2": "array",
    }

    # for dataset filtering
    DATASETS_FIELDS_TO_TYPES = {
        "checkbox": ["string"],
        "id": ["integer"],
        "dataset_id": ["string"],
        "project_id": ["string"],
        "name": ["string"],
        "disease": ["string"],
        "treatment": ["string"],
        "molecularInfo": ["string"],
        "sampleType": ["string"],
        "dataType": ["string"],
        "valueType": ["string"],
        "platform": ["string"],
        "genomeAssembly": ["string"],
        "annotation": ["string"],
        "samplesCount": ["string", "integer"],
        "featuresCount": ["string", "integer"],
        "featuresID": "string",
        "healthyControllsIncluded": ["string", "boolean"],
        "additionalInfo": "string",
        "contact": "string",
        "tags": "string",
        "visibility": "string",
        "submitter_name": "string",
        "submit_date": "string",
        "shared_with": "string",
    }

    # needs more API tests
    # + end to end test
    PROJECTS_FIELDS_TO_TYPES = {
        "id": ["string"],
        "project_id": ["string"],
        "name": ["string"],
        "description": ["string"],
        "owners": ["string"],
        "diseases": ["string"],
        "logo_url": ["string"],
        "dataset_visibility_changeable": ["boolean"],
        "dataset_visibility_default": ["string"],
        "file_dl_allowed": ["boolean"],
    }

    PROJECTS_FIELDS = [
        "id",
        "name",
        "description",
        "owners",
        "datasetVisibilityDefault",
        "datasetVisibilityChangeable",
        "fileDlAllowed",
        "diseases",
    ]

    PROJECTS_EXTRA_COLS = [
        "description",
        "diseases",
        "logo_url",
        "dataset_visibility_changeable",
        "dataset_visibility_default",
        "file_dl_allowed",
    ]

    DATASET_FIELDS_ENUMS = {
        "disease": ["COPD", "ASTHMA", "CD", "UC", "MS", "SLE", "RA"],
        "visibility": ["private", "visible to all"],
    }

    # File Upload
    ALLOWED_FILE_EXTENSIONS = ["tsv", "csv", "txt", "gz", "rds", "rda", "h5ad"]

    FILE_FIELDS = [
        "projectId",
        "DatasetID",
        "file",
        "fileName",
        "Comment",
    ]

    # Data Management
    VIEW_FIELDS_TYPES = {
        "page": "integer",
        "pageSize": "integer",
        "sorted": ["array", "null"],
        "filtered": ["array", "null"],
    }

    GENERAL_VIEW_FIELDS = [["page", "pageSize"], ["sorted", "filtered"]]

    FILTERED_FIELDS_TYPES = {"id": "string", "value": "string"}

    SORTED_FIELDS_TYPES = {"id": "string", "desc": "boolean"}

    # React table id to sql column name w/o extra_cols
    PROJECT_COL_MAPPING = {
        "id": "project_id",
        "project_id": "project_id",
        "name": "name",
        "owners": "owners",
        # "description": "description",
        # "datasetVisibilityDefault": "dataset_visibility_default",
        # "datasetVisibilityChangeable": "dataset_visibility_changeable",
        # "fileDlAllowed": "file_dl_allowed",
        # "diseases": "diseases",
        # "logoUrl": "logo_url",
    }

    # below is for dataset view
    PROJECTS_COL_MAPPING = {
        "id": "project_id",
        "project_id": "project_id",
        "name": "name",
        "owners": "owners",
        # "description": "description",
        # "datasetVisibilityDefault": "dataset_visibility_default",
        # "datasetVisibilityChangeable": "dataset_visibility_changeable",
        # "fileDlAllowed": "file_dl_allowed",
        # "diseases": "diseases",
        # "logoUrl": "logo_url",
    }

    DATASETS_COL_MAPPING = {
        "id": "id",
        "dataset_id": "dataset_id",
        "project_id": "project_id",
        "name": "name",
        # "disease": "disease",
        # "treatment": "treatment",
        # "molecularInfo": "molecular_info",
        # "sampleType": "sample_type",
        # "dataType": "data_type",
        # "valueType": "value_type",
        # "platform": "platform",
        # "genomeAssembly": "genome_assembly",
        # "annotation": "annotation",
        # "samplesCount": "samples_count",
        # "featuresCount": "features_count",
        # "featuresID": "features_id",
        # "healthyControllsIncluded": "healthy_control_included",
        # "additionalInfo": "additional_info",
        # "contact": "contact",
        # "tags": "tags",
        "visibility": "private",
        "submitter_name": "submitter_name",
        "submit_date": "submission_date",
        "shared_with": "shared_with",
    }

    # Somehow I need both DATASET_COL_MAPPING and DATASETS_COL_MAPPING
    DATASET_COL_MAPPING = {
        "id": "dataset_id",
        "project_id": "project_id",
        "name": "name",
        "disease": "disease",
        "treatment": "treatment",
        "molecularInfo": "molecular_info",
        "sampleType": "sample_type",
        "dataType": "data_type",
        "valueType": "value_type",
        "platform": "platform",
        "genomeAssembly": "genome_assembly",
        "annotation": "annotation",
        "samplesCount": "samples_count",
        "featuresCount": "features_count",
        "featuresID": "features_id",
        "healthyControllsIncluded": "healthy_control_included",
        "additionalInfo": "additional_info",
        "contact": "contact",
        "tags": "tags",
        "visibility": "private",
        "submitter_name": "submitter_name",
        "submit_date": "submission_date",
        "shared_with": "shared_with",
        "file": "file",
        "file2": "file2",
    }

    FILES_COL_MAPPING = {
        "id": "id",
        "dataset_id": "dataset_id",
        "name": "name",
        "version": "version",
        "submitter_name": "submitter_name",
        "submit_date": "submission_date",
        "shared_with": "shared_with",
    }

    # for filtering files
    FILES_FIELDS_TO_TYPES = {
        "id": ["integer", "string"],
        "name": ["string"],
        "version": ["string", "integer"],
        "project_id": ["string"],
        "dataset_id": ["string"],
        "submitter_name": ["string"],
        "submit_date": ["string"],
        "shared_with": ["string"],
        "visibility": ["string"],
        "checkbox": ["string"],  # for filtering the owner column
    }

    # keys in the json of the key "extra_cols"
    DATASETS_EXTRA_COLS = [
        "disease",
        "treatment",
        "molecularInfo",
        "sampleType",
        "dataType",
        "valueType",
        "platform",
        "genomeAssembly",
        "annotation",
        "samplesCount",
        "featuresCount",
        "featuresID",
        "healthyControllsIncluded",
        "additionalInfo",
        "contact",
        "tags",
        "file",
        "file2",
    ]

    DATASETS_EXTRA_COLS_MAPPING = {
        "disease": "disease",
        "treatment": "treatment",
        "molecularInfo": "molecular_info",
        "sampleType": "sample_type",
        "dataType": "data_type",
        "valueType": "value_type",
        "platform": "platform",
        "genomeAssembly": "genome_assembly",
        "annotation": "annotation",
        "samplesCount": "samples_count",
        "featuresCount": "features_count",
        "featuresID": "features_id",
        "healthyControllsIncluded": "healthy_control_included",
        "additionalInfo": "additional_info",
        "contact": "contact",
        "tags": "tags",
        "file": "file",
        "file2": "file2",
    }

    FILES_EXTRA_COLS = ["comment"]
