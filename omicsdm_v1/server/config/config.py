class Config(object):
    """
    config for 3TR
    """

    # postgres
    # SQLALCHEMY_DATABASE_URI = "postgresql://devel_omicsdm_3tr_rw:pass@172.17.0.5:5432/v1"
    SQLALCHEMY_DATABASE_URI = "postgresql://odmv1:pass@10.10.0.2:5432/odmv1"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # jwt
    SECRET_KEY = "othrt-some-secret-string"
    JWT_SECRET_KEY = "jwt-secret-string"
    JWT_OPTIONS = {"verify_exp": False, "verify_aud": False}

    # keycloak
    AUTH_BASE_URL="http://10.10.0.3:8080"
    AUTH_REALM="3TR"
    IDRSA="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0juOxC3+S97HFnlmRgWqUaSpTlscaH6IQaoLuqXFYakDJCV6WU0andDRQFJH8CeOaiVx84J1g7m/cNzxX6Ilz+0MZ6mnBFShaGY0+Qk6zIipFU2ehWQtAm0IWGwQipXC2enlXLIglRXJJepH7jOxC+fyY+f++09+68KuNAAUL8IjvZRMCu/AV3qlm6zdeCztTxy8eiBH9shg+wNLRpWczfMBAHetqqpzy9kVhVizHFdSxd21yESRce7iUQn+KzwsGzBve0Ds68GzhgyUXYjXV/sQ3jaNqDAy+qiCkv0nXKPBxVFUstPQQJvhlQ4gZW7SUdIV3IynBXckpGQhE24tcQIDAQAB"
    KC_CLIENT_ID="submission_client"
    KC_CLIENT_SECRET="38wBvfSVS7fa3LprqSL5YCDPaMUY1bTl"

    # ceph # Not used for the benchmark
    CEPH_URL = "secret"
    BUCKET_NAME = "secret"
    ACCESS_KEY = "secret"
    SECRET_KEY = "secret"

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

    # possible values based on "profiling menue"
    DATASET_FIELDS_ENUMS = {
        "disease": ["COPD", "ASTHMA", "CD", "UC", "MS", "SLE", "RA"],
        "category": [
            "Sequencing, genotyping, arrays",
            "Imaging and histology/pathology",
            "Protocols for CyTOF, blood cell separation and cell metabolome",
            "Proteomics and metabolomics",
            "Exosomes and microvescicles",
            "Microbiome",
            "Bioinformatics/Statistical and other analyses",
            "other",
        ],
    }

    # File Upload
    ALLOWED_FILE_EXTENSIONS = ["tsv", "csv", "txt", "gz", "rds", "rda", "h5ad"]

    FILE_FIELDS = ["DatasetID", "File","fileName", "Platform", "Comment"]

    # possible values based on profiling menue
    FILE_FIELDS_ENUMS = {
        "Platform": [
            "EPIC arrays 96 samples",
            "Pyrosequencing",
            "Agilent",
            "Affy arrays",
            "OMINI 5 Illumina array",
            "IntelliQube",
            "SCRNASeq",
            "scmiRNASeq",
            "ATACSeq",
            "SCRNASeq",
            "WGBS",
            "RNASeq",
            "Hyperion",
            "multiplexed immunofluorescence and normal histology",
            "HELIOS and MS-based Fluxomics",
            "LC-MS",
            "UHPLC",
            "CGE",
            "OLINK",
            "ELISAs",
            "various routine",
            "Luminex Human Atlas Proteins",
            "MSD platform",
            "NMR",
            "extraction",
            "NGS",
            "metagenomics or 16SrRNA sequencing",
            "Flow",
            "metagenome",
            "computational modelling",
            "other (please specify in comments)",
            "other",
        ]
    }

    # Analysis Submission
    ANALYSIS_FIELDS = general_fields + [
        "selected_datasets",
        "selected_files",
    ]  # types = list of strings

    # Data Management
    VIEW_FIELDS_TYPES = {
        "page": "integer",
        "pageSize": "integer",
        "sorted": ["array", "null"],
        "filtered": ["array", "null"],
    }

    FILTERED_FIELDS_TYPES = {"id": "string", "value": "string"}
    SORTED_FIELDS_TYPES = {"id": "string", "desc": "boolean"}

    # React table id to sql column name
    FILES_COL_MAPPING = {
        "id": "id",
        "name": "name",
        "version": "version",
        "dataset_id": "dataset_id",
        "submitter_name": "submitter_name",
        "submit_date": "submission_date",
        "platform": "platform",
        "comment": "comment",
        "shared_with": "shared_with",
    }

    ANALYSIS_COL_MAPPING = {
        "id": "id",
        "name": "name",
        "analysis_id": "analysis_id",
        "submitter_name": "submitter_name",
        "submit_date": "submission_date",
        "shared_with": "shared_with",
    }
    DATASETS_COL_MAPPING = {
        "id": "dataset_id",
        "name": "name",
        "desc": "description",
        "tags": "tags",
        "partners": "responsible_partner",
        "disease": "disease",
        "treatment": "treatment",
        "cat": "category",
        "visibility": "private",
        "submitter_name": "submitter_name",
        "submit_date": "submission_date",
        "shared_with": "shared_with",
    }
