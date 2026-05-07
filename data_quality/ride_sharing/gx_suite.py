import logging
import os
import urllib.parse

import great_expectations as gx
import snowflake.connector
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
SF_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SF_USER = os.getenv("SNOWFLAKE_USER")
SF_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SF_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SF_SCHEMA = "RAW"
SF_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SF_ROLE = os.getenv("SNOWFLAKE_ROLE")

# 1. Initialize Great Expectations Context
context = gx.get_context(mode="ephemeral")
logger.info("✅ GX Context Initialized.")

# 2. Connect to Snowflake using SQLAlchemy string for GX
# URL-encode the password to safely pass special characters like $ and #
SF_PASSWORD_ENCODED = urllib.parse.quote_plus(SF_PASSWORD)
connection_string = (
    f"snowflake://{SF_USER}:{SF_PASSWORD_ENCODED}@{SF_ACCOUNT}/"
    f"{SF_DATABASE}/{SF_SCHEMA}?warehouse={SF_WAREHOUSE}&role={SF_ROLE}"
)

logger.info("Connecting GX to Snowflake...")
datasource = context.data_sources.add_snowflake(
    name="snowflake_ride_sharing", connection_string=connection_string
)

# Define the asset (our View)
asset = datasource.add_table_asset(name="raw_gps_asset", table_name="VW_RAW_GPS")
batch_definition = asset.add_batch_definition_whole_table("whole_table_batch")

# 3. Define the Expectation Suite
suite_name = "gps_quality_suite"
suite = gx.ExpectationSuite(name=suite_name)

# Expectation 1: Speed must be realistic (0 to 120 MPH)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="SPEED_MPH", min_value=0.0, max_value=120.0
    )
)

# Expectation 2: Coordinates must be roughly within New York boundaries
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="LATITUDE", min_value=40.0, max_value=42.0
    )
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="LONGITUDE", min_value=-75.0, max_value=-72.0
    )
)

# Expectation 3: Driver ID must not be null
suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="DRIVER_ID"))

context.suites.add(suite)
logger.info("✅ Expectation Suite built.")

# 4. Run the Validation
logger.info("🔍 Running Great Expectations Validation against VW_RAW_GPS...")
validation_definition = context.validation_definitions.add(
    gx.ValidationDefinition(name="gps_validation", data=batch_definition, suite=suite)
)

validation_results = validation_definition.run()

# 5. Report Results
success = validation_results.success
logger.info(f"Great Expectations Suite Passed: {success}")

# Print out exactly how many anomalies were caught!
for result in validation_results.results:
    expectation_type = result.expectation_config.type
    column = result.expectation_config.kwargs.get("column")
    unexpected_count = result.result.get("unexpected_count", 0)
    element_count = result.result.get("element_count", 0)

    if unexpected_count > 0:
        logger.warning(
            f"❌ {expectation_type} on {column} FAILED! "
            f"Caught {unexpected_count} anomalies out of {element_count} total pings."
        )
    else:
        logger.info(f"✅ {expectation_type} on {column} PASSED! (0 anomalies)")


# 6. Route Valid Data to CLEAN_GPS Table
logger.info("🧹 Routing clean data to CLEAN_GPS table...")
conn = snowflake.connector.connect(
    user=SF_USER,
    password=SF_PASSWORD,
    account=SF_ACCOUNT,
    warehouse=SF_WAREHOUSE,
    database=SF_DATABASE,
    schema=SF_SCHEMA,
    role=SF_ROLE,
)
cursor = conn.cursor()

# We use standard SQL to filter out the anomalies based on the exact same GX rules
clean_sql = """
CREATE OR REPLACE TABLE CLEAN_GPS AS
SELECT * FROM VW_RAW_GPS
WHERE SPEED_MPH BETWEEN 0.0 AND 120.0
  AND LATITUDE BETWEEN 40.0 AND 42.0
  AND LONGITUDE BETWEEN -75.0 AND -72.0
  AND DRIVER_ID IS NOT NULL;
"""
cursor.execute(clean_sql)
logger.info("🚀 Clean data successfully routed to CLEAN_GPS table!")
cursor.close()
conn.close()
