import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DataSpark | Global Electronics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "Data_Spark.db"


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.7rem;
        font-weight: 700;
    }

    .dashboard-title {
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 0;
    }

    .dashboard-subtitle {
        color: #777;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create a connection to the SQLite database.
    """

    if not DB_PATH.exists():
        st.error(
            f"""
            Database not found.

            Expected location:

            {DB_PATH}

            Make sure `Data_Spark.db` is in the same folder as `app.py`.
            """
        )
        st.stop()

    return sqlite3.connect(DB_PATH)


# ============================================================
# DATABASE UTILITIES
# ============================================================

@st.cache_data(ttl=600)
def get_tables():

    conn = get_connection()

    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df["name"].tolist()


@st.cache_data(ttl=600)
def get_columns(table_name):

    conn = get_connection()

    query = f'PRAGMA table_info("{table_name}")'

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


@st.cache_data(ttl=600)
def execute_query(query, params=()):

    conn = get_connection()

    try:

        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

        return df

    except Exception as e:

        st.error(f"SQL Error: {e}")

        return pd.DataFrame()

    finally:

        conn.close()


# ============================================================
# CHECK DATABASE
# ============================================================

tables = get_tables()

if not tables:

    st.error("No tables were found inside Data_Spark.db.")
    st.stop()


if "MergedData" not in tables:

    st.warning(
        """
        The database does not contain a table named `MergedData`.

        Available tables:
        """
    )

    st.write(tables)

    st.stop()


# ============================================================
# FILTER DATA
# ============================================================

@st.cache_data(ttl=600)
def get_filter_data():

    countries = execute_query(
        """
        SELECT DISTINCT "Country_x"
        FROM MergedData
        WHERE "Country_x" IS NOT NULL
        ORDER BY "Country_x"
        """
    )["Country_x"].tolist()

    categories = execute_query(
        """
        SELECT DISTINCT "Category"
        FROM MergedData
        WHERE "Category" IS NOT NULL
        ORDER BY "Category"
        """
    )["Category"].tolist()

    brands = execute_query(
        """
        SELECT DISTINCT "Brand"
        FROM MergedData
        WHERE "Brand" IS NOT NULL
        ORDER BY "Brand"
        """
    )["Brand"].tolist()

    genders = execute_query(
        """
        SELECT DISTINCT "Gender"
        FROM MergedData
        WHERE "Gender" IS NOT NULL
        ORDER BY "Gender"
        """
    )["Gender"].tolist()

    dates = execute_query(
        """
        SELECT
            MIN(date("Order Date")) AS MinDate,
            MAX(date("Order Date")) AS MaxDate
        FROM MergedData
        """
    )

    return (
        countries,
        categories,
        brands,
        genders,
        dates.iloc[0]["MinDate"],
        dates.iloc[0]["MaxDate"],
    )


(
    countries,
    categories,
    brands,
    genders,
    min_date,
    max_date,
) = get_filter_data()


min_date = pd.to_datetime(min_date).date()
max_date = pd.to_datetime(max_date).date()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 DataSpark")

st.sidebar.caption(
    "Global Electronics Analytics Dashboard"
)

st.sidebar.divider()

st.sidebar.subheader("🔎 Filters")


# Date filter

date_range = st.sidebar.date_input(
    "Order Date",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)


if isinstance(date_range, tuple) and len(date_range) == 2:

    start_date = date_range[0]
    end_date = date_range[1]

else:

    start_date = min_date
    end_date = max_date


# Country

selected_countries = st.sidebar.multiselect(
    "Country",
    countries,
)


# Category

selected_categories = st.sidebar.multiselect(
    "Category",
    categories,
)


# Brand

selected_brands = st.sidebar.multiselect(
    "Brand",
    brands,
)


# Gender

selected_genders = st.sidebar.multiselect(
    "Gender",
    genders,
)


# ============================================================
# BUILD FILTER CONDITIONS
# ============================================================

def build_filter():

    conditions = [
        'date("Order Date") BETWEEN date(?) AND date(?)'
    ]

    params = [
        str(start_date),
        str(end_date)
    ]

    if selected_countries:

        placeholders = ",".join(
            ["?"] * len(selected_countries)
        )

        conditions.append(
            f'"Country_x" IN ({placeholders})'
        )

        params.extend(selected_countries)

    if selected_categories:

        placeholders = ",".join(
            ["?"] * len(selected_categories)
        )

        conditions.append(
            f'"Category" IN ({placeholders})'
        )

        params.extend(selected_categories)

    if selected_brands:

        placeholders = ",".join(
            ["?"] * len(selected_brands)
        )

        conditions.append(
            f'"Brand" IN ({placeholders})'
        )

        params.extend(selected_brands)

    if selected_genders:

        placeholders = ",".join(
            ["?"] * len(selected_genders)
        )

        conditions.append(
            f'"Gender" IN ({placeholders})'
        )

        params.extend(selected_genders)

    return " AND ".join(conditions), params


WHERE_CLAUSE, FILTER_PARAMS = build_filter()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_currency(value):

    if value is None or pd.isna(value):
        return "$0"

    return f"${value:,.2f}"


def format_number(value):

    if value is None or pd.isna(value):
        return "0"

    return f"{int(value):,}"


def section_title(title, subtitle=None):

    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )

    if subtitle:
        st.caption(subtitle)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="dashboard-title">📊 DataSpark</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="dashboard-subtitle">'
    'Global Electronics Business Intelligence Dashboard'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# KPI CALCULATION
# ============================================================

kpi_query = f"""

SELECT

    COUNT(DISTINCT "Order Number") AS Total_Orders,

    COUNT(DISTINCT "Customer_ID") AS Total_Customers,

    SUM("Quantity") AS Total_Units,

    SUM(
        "Unit Price USD" * "Quantity"
    ) AS Total_Revenue,

    SUM(
        ("Unit Price USD" - "Unit Cost USD")
        * "Quantity"
    ) AS Total_Profit

FROM MergedData

WHERE {WHERE_CLAUSE}

"""


kpi_df = execute_query(
    kpi_query,
    FILTER_PARAMS
)


if not kpi_df.empty:

    kpi = kpi_df.iloc[0]

else:

    kpi = {
        "Total_Orders": 0,
        "Total_Customers": 0,
        "Total_Units": 0,
        "Total_Revenue": 0,
        "Total_Profit": 0,
    }


# ============================================================
# KPI CARDS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

with c1:

    st.metric(
        "📦 Orders",
        format_number(kpi["Total_Orders"])
    )

with c2:

    st.metric(
        "👥 Customers",
        format_number(kpi["Total_Customers"])
    )

with c3:

    st.metric(
        "📊 Units Sold",
        format_number(kpi["Total_Units"])
    )

with c4:

    st.metric(
        "💰 Revenue",
        format_currency(kpi["Total_Revenue"])
    )

with c5:

    st.metric(
        "📈 Gross Profit",
        format_currency(kpi["Total_Profit"])
    )


st.divider()


# ============================================================
# NAVIGATION
# ============================================================

page = st.sidebar.radio(
    "📍 Dashboard",
    [
        "🏠 Overview",
        "👥 Customer Analytics",
        "💰 Sales Analytics",
        "📦 Product Analytics",
        "🏪 Store Analytics",
        "🧠 Advanced Analytics",
        "🗃️ Data Explorer",
    ]
)


# ============================================================
# OVERVIEW
# ============================================================

if page == "🏠 Overview":

    st.header("🏠 Business Overview")

    # --------------------------------------------------------
    # Sales Trend
    # --------------------------------------------------------

    section_title(
        "Overall Sales Performance",
        "Monthly revenue trend."
    )

    sales_query = f"""

    SELECT

        strftime('%Y-%m', "Order Date") AS Month,

        SUM(
            "Unit Price USD" * "Quantity"
        ) AS Total_Sales

    FROM MergedData

    WHERE {WHERE_CLAUSE}

    GROUP BY
        strftime('%Y-%m', "Order Date")

    ORDER BY Month

    """

    sales_df = execute_query(
        sales_query,
        FILTER_PARAMS
    )


    if not sales_df.empty:

        fig = px.line(
            sales_df,
            x="Month",
            y="Total_Sales",
            markers=True,
            title="Monthly Sales"
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Sales (USD)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # --------------------------------------------------------
    # Two columns
    # --------------------------------------------------------

    col1, col2 = st.columns(2)


    # --------------------------------------------------------
    # Top Products
    # --------------------------------------------------------

    with col1:

        section_title(
            "Top Performing Products",
            "Products ranked by revenue."
        )

        query = f"""

        SELECT

            "Product Name",

            SUM("Quantity")
                AS Total_Quantity_Sold,

            SUM(
                "Unit Price USD" * "Quantity"
            ) AS Total_Revenue

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Product Name"

        ORDER BY Total_Revenue DESC

        LIMIT 10

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            fig = px.bar(
                df.sort_values("Total_Revenue"),
                x="Total_Revenue",
                y="Product Name",
                orientation="h",
                title="Top 10 Products"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    with col2:

        section_title(
            "Sales by Category"
        )

        query = f"""

        SELECT

            "Category",

            SUM(
                "Unit Price USD" * "Quantity"
            ) AS Total_Sales

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Category"

        ORDER BY Total_Sales DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            fig = px.pie(
                df,
                names="Category",
                values="Total_Sales",
                title="Revenue by Category"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# CUSTOMER ANALYTICS
# ============================================================

elif page == "👥 Customer Analytics":

    st.header("👥 Customer Analytics")


    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Demographics",
            "Purchase Patterns",
            "Segmentation",
            "Retention",
        ]
    )


    # ========================================================
    # DEMOGRAPHICS
    # ========================================================

    with tab1:

        section_title(
            "Customer Demographic Insights",
            "Gender, age and geographical distribution."
        )


        query = f"""

        SELECT

            "Gender",

            COUNT(DISTINCT "Customer_ID")
                AS Total_Customers,

            ROUND(
                AVG("Age"), 1
            ) AS Average_Age,

            "City",

            "State_x" AS State,

            "Country_x" AS Country,

            "Continent"

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY
            "Gender",
            "City",
            "State_x",
            "Country_x",
            "Continent"

        ORDER BY Total_Customers DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        col1, col2 = st.columns(2)


        # Gender

        gender_query = f"""

        SELECT

            "Gender",

            COUNT(DISTINCT "Customer_ID")
                AS Customers

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Gender"

        ORDER BY Customers DESC

        """

        gender_df = execute_query(
            gender_query,
            FILTER_PARAMS
        )


        # Age

        age_query = f"""

        SELECT

            CASE

                WHEN "Age" < 25
                    THEN 'Under 25'

                WHEN "Age" BETWEEN 25 AND 40
                    THEN '25-40'

                WHEN "Age" BETWEEN 41 AND 60
                    THEN '41-60'

                ELSE 'Above 60'

            END AS Age_Group,

            COUNT(DISTINCT "Customer_ID")
                AS Customers

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY Age_Group

        ORDER BY Customers DESC

        """

        age_df = execute_query(
            age_query,
            FILTER_PARAMS
        )


        with col1:

            fig = px.pie(
                gender_df,
                names="Gender",
                values="Customers",
                title="Gender Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        with col2:

            fig = px.bar(
                age_df,
                x="Age_Group",
                y="Customers",
                title="Age Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # PURCHASE PATTERNS
    # ========================================================

    with tab2:

        section_title(
            "Customer Purchase Patterns"
        )


        query = f"""

        SELECT

            "Customer_ID",

            COUNT(
                DISTINCT "Order Number"
            ) AS Purchase_Frequency,

            ROUND(

                SUM(
                    "Unit Price USD" * "Quantity"
                )
                /
                NULLIF(
                    COUNT(DISTINCT "Order Number"),
                    0
                ),

                2

            ) AS Average_Order_Value,

            GROUP_CONCAT(
                DISTINCT "Product Name"
            ) AS Preferred_Products

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Customer_ID"

        ORDER BY Average_Order_Value DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # SEGMENTATION
    # ========================================================

    with tab3:

        section_title(
            "Customer Segmentation",
            "Customers segmented by age and spending."
        )


        query = f"""

        WITH Customer_Spend AS (

            SELECT

                "Customer_ID",

                SUM(
                    "Unit Price USD" * "Quantity"
                ) AS Total_Spend,

                AVG("Age")
                    AS Average_Age

            FROM MergedData

            WHERE {WHERE_CLAUSE}

            GROUP BY "Customer_ID"

        )

        SELECT

            CASE

                WHEN Average_Age < 25
                    THEN 'Under 25'

                WHEN Average_Age BETWEEN 25 AND 40
                    THEN '25-40'

                WHEN Average_Age BETWEEN 41 AND 60
                    THEN '41-60'

                ELSE 'Above 60'

            END AS Age_Segment,

            CASE

                WHEN Total_Spend < 100
                    THEN 'Low Spend'

                WHEN Total_Spend BETWEEN 100 AND 500
                    THEN 'Medium Spend'

                ELSE 'High Spend'

            END AS Spend_Segment,

            COUNT(*) AS Number_of_Customers

        FROM Customer_Spend

        GROUP BY
            Age_Segment,
            Spend_Segment

        ORDER BY
            Age_Segment,
            Spend_Segment

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        if not df.empty:

            pivot = df.pivot(
                index="Age_Segment",
                columns="Spend_Segment",
                values="Number_of_Customers"
            ).fillna(0)


            fig = px.bar(
                pivot,
                barmode="group",
                title="Customer Segmentation"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # RETENTION
    # ========================================================

    with tab4:

        section_title(
            "Customer Retention Analysis",
            "Based on the 365-day retention rule from your SQL analysis."
        )


        query = f"""

        WITH CustomerOrders AS (

            SELECT

                "CustomerKey",

                MIN("Order Date")
                    AS FirstPurchase,

                MAX("Order Date")
                    AS LastPurchase,

                COUNT(
                    DISTINCT "Order Number"
                ) AS TotalOrders

            FROM MergedData

            WHERE {WHERE_CLAUSE}

            GROUP BY "CustomerKey"

        )

        SELECT

            "CustomerKey",

            FirstPurchase,

            LastPurchase,

            TotalOrders,

            CASE

                WHEN
                    julianday('now')
                    - julianday(LastPurchase)
                    <= 365

                THEN 'Retained'

                ELSE 'Churned'

            END AS CustomerStatus

        FROM CustomerOrders

        ORDER BY TotalOrders DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        if not df.empty:

            status_df = (
                df.groupby("CustomerStatus")
                .size()
                .reset_index(name="Customers")
            )


            fig = px.pie(
                status_df,
                names="CustomerStatus",
                values="Customers",
                title="Customer Retention"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# SALES ANALYTICS
# ============================================================

elif page == "💰 Sales Analytics":

    st.header("💰 Sales Analytics")


    tab1, tab2, tab3 = st.tabs(
        [
            "Sales Trend",
            "Currency Impact",
            "Promotion Impact",
        ]
    )


    # ========================================================
    # SALES TREND
    # ========================================================

    with tab1:

        section_title(
            "Overall Sales Performance"
        )


        query = f"""

        SELECT

            strftime(
                '%m',
                "Order Date"
            ) AS Month,

            strftime(
                '%Y',
                "Order Date"
            ) AS Year,

            SUM(
                "Unit Price USD" * "Quantity"
            ) AS Total_Sales

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY
            Year,
            Month

        ORDER BY
            Year,
            Month

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            df["Period"] = (
                df["Year"]
                + "-"
                + df["Month"]
            )


            fig = px.line(
                df,
                x="Period",
                y="Total_Sales",
                markers=True,
                title="Sales Trend"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # CURRENCY
    # ========================================================

    with tab2:

        section_title(
            "Impact of Currency on Sales"
        )


        query = f"""

        SELECT

            "Currency Code",

            SUM(
                "Unit Price USD" * "Quantity"
            ) AS Total_Sales,

            AVG(
                "Unit Cost USD"
            ) AS Average_Cost,

            AVG(
                "Unit Price USD"
            ) AS Average_Price

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Currency Code"

        ORDER BY Total_Sales DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        fig = px.bar(
            df,
            x="Currency Code",
            y="Total_Sales",
            title="Sales by Currency"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # ========================================================
    # PROMOTION
    # ========================================================

    with tab3:

        section_title(
            "Impact of Promotions on Sales"
        )


        query = f"""

        SELECT

            strftime(
                '%Y-%m',
                "Order Date"
            ) AS Month,

            SUM(

                CASE

                    WHEN
                        "Unit Price USD"
                        <
                        "Unit Cost USD"

                    THEN
                        "Unit Price USD"
                        *
                        "Quantity"

                    ELSE 0

                END

            ) AS Discounted_Sales,

            SUM(
                "Unit Price USD"
                *
                "Quantity"
            ) AS Total_Sales,

            (

                SUM(

                    CASE

                        WHEN
                            "Unit Price USD"
                            <
                            "Unit Cost USD"

                        THEN
                            "Unit Price USD"
                            *
                            "Quantity"

                        ELSE 0

                    END

                )

                /

                NULLIF(

                    SUM(
                        "Unit Price USD"
                        *
                        "Quantity"
                    ),

                    0

                )

            ) * 100

            AS Discounted_Sales_Percentage

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY
            strftime(
                '%Y-%m',
                "Order Date"
            )

        ORDER BY Month

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        if not df.empty:

            fig = px.line(
                df,
                x="Month",
                y="Discounted_Sales_Percentage",
                markers=True,
                title="Discounted Sales Percentage"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# PRODUCT ANALYTICS
# ============================================================

elif page == "📦 Product Analytics":

    st.header("📦 Product Analytics")


    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Top Products",
            "Profitability",
            "Movement",
            "Inventory",
        ]
    )


    # ========================================================
    # TOP PRODUCTS
    # ========================================================

    with tab1:

        section_title(
            "Top-Performing Products"
        )


        query = f"""

        SELECT

            "Product Name",

            SUM("Quantity")
                AS Total_Quantity_Sold,

            SUM(
                "Unit Price USD"
                *
                "Quantity"
            ) AS Total_Revenue

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Product Name"

        ORDER BY Total_Revenue DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            fig = px.bar(
                df.head(15).sort_values(
                    "Total_Revenue"
                ),
                x="Total_Revenue",
                y="Product Name",
                orientation="h",
                title="Top 15 Products"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # PROFITABILITY
    # ========================================================

    with tab2:

        section_title(
            "Product Profitability"
        )


        query = f"""

        SELECT

            "Product Name",

            AVG(
                "Unit Price USD"
                -
                "Unit Cost USD"
            ) AS Average_Profit_Margin,

            AVG(
                "Unit Price USD"
            ) AS Average_Selling_Price,

            AVG(
                "Unit Cost USD"
            ) AS Average_Cost

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Product Name"

        ORDER BY
            Average_Profit_Margin DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            fig = px.bar(
                df.head(15).sort_values(
                    "Average_Profit_Margin"
                ),
                x="Average_Profit_Margin",
                y="Product Name",
                orientation="h",
                title="Top Products by Profit Margin"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # MOVEMENT
    # ========================================================

    with tab3:

        section_title(
            "Product Movement Status",
            "Products with fewer than 50 units sold are classified as Slow-Moving."
        )


        query = f"""

        SELECT

            "Product Name",

            SUM("Quantity")
                AS Total_Quantity_Sold,

            COUNT(
                DISTINCT "Order Number"
            ) AS Total_Orders,

            CASE

                WHEN
                    SUM("Quantity") < 50

                THEN
                    'Slow-Moving'

                ELSE
                    'Fast-Moving'

            END AS Product_Movement_Status

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Product Name"

        HAVING
            Total_Quantity_Sold < 50

        ORDER BY
            Total_Quantity_Sold ASC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # INVENTORY
    # ========================================================

    with tab4:

        section_title(
            "Inventory Turnover Analysis"
        )


        query = f"""

        SELECT

            "Product Name",

            SUM("Quantity")
                AS TotalQuantitySold,

            AVG("Unit Cost USD")
                AS AverageCost,

            (

                SUM("Quantity")
                /
                NULLIF(
                    AVG("Square Meters"),
                    0
                )

            ) AS InventoryTurnoverRatio

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY "Product Name"

        ORDER BY
            InventoryTurnoverRatio DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            fig = px.bar(
                df.head(15).sort_values(
                    "InventoryTurnoverRatio"
                ),
                x="InventoryTurnoverRatio",
                y="Product Name",
                orientation="h",
                title="Inventory Turnover"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# STORE ANALYTICS
# ============================================================

elif page == "🏪 Store Analytics":

    st.header("🏪 Store Analytics")


    query = f"""

    SELECT

        StoreKey,

        SUM(
            "Unit Price USD"
            *
            "Quantity"
        ) AS Total_Sales,

        AVG(
            "Square Meters"
        ) AS Average_Store_Size

    FROM MergedData

    WHERE {WHERE_CLAUSE}

    GROUP BY StoreKey

    ORDER BY Total_Sales DESC

    """

    df = execute_query(
        query,
        FILTER_PARAMS
    )


    col1, col2 = st.columns(2)


    with col1:

        fig = px.bar(
            df.head(15).sort_values(
                "Total_Sales"
            ),
            x="Total_Sales",
            y="StoreKey",
            orientation="h",
            title="Top Stores by Sales"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


    with col2:

        fig = px.scatter(
            df,
            x="Average_Store_Size",
            y="Total_Sales",
            hover_name="StoreKey",
            title="Store Size vs Sales"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ADVANCED ANALYTICS
# ============================================================

elif page == "🧠 Advanced Analytics":

    st.header("🧠 Advanced Analytics")


    tab1, tab2, tab3 = st.tabs(
        [
            "Product Affinity",
            "Customer Lifetime Value",
            "Seasonality",
        ]
    )


    # ========================================================
    # PRODUCT AFFINITY
    # ========================================================

    with tab1:

        section_title(
            "Product Affinity Analysis",
            "Products frequently purchased together."
        )


        query = f"""

        WITH OrderProducts AS (

            SELECT DISTINCT

                "Order Number",

                "Product Name"

            FROM MergedData

            WHERE {WHERE_CLAUSE}

        ),

        ProductPairs AS (

            SELECT

                a."Product Name"
                    AS Product_A,

                b."Product Name"
                    AS Product_B

            FROM OrderProducts a

            JOIN OrderProducts b

                ON
                    a."Order Number"
                    =
                    b."Order Number"

                AND
                    a."Product Name"
                    <
                    b."Product Name"

        )

        SELECT

            Product_A,

            Product_B,

            COUNT(*)
                AS CoPurchaseFrequency

        FROM ProductPairs

        GROUP BY
            Product_A,
            Product_B

        ORDER BY
            CoPurchaseFrequency DESC

        LIMIT 20

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        if not df.empty:

            df["Product Pair"] = (
                df["Product_A"]
                + " + "
                + df["Product_B"]
            )


            fig = px.bar(
                df.sort_values(
                    "CoPurchaseFrequency"
                ),
                x="CoPurchaseFrequency",
                y="Product Pair",
                orientation="h",
                title="Top Product Pairs"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # CLV
    # ========================================================

    with tab2:

        section_title(
            "Customer Lifetime Value",
            "Customers with more than one order."
        )


        query = f"""

        WITH CustomerSpend AS (

            SELECT

                "CustomerKey",

                SUM(
                    "Unit Price USD"
                    *
                    "Quantity"
                ) AS TotalSpend,

                COUNT(
                    DISTINCT "Order Number"
                ) AS TotalOrders,

                MIN("Order Date")
                    AS FirstOrderDate,

                MAX("Order Date")
                    AS LastOrderDate

            FROM MergedData

            WHERE {WHERE_CLAUSE}

            GROUP BY "CustomerKey"

        )

        SELECT

            "CustomerKey",

            TotalSpend,

            TotalOrders,

            ROUND(

                TotalSpend
                /
                NULLIF(
                    TotalOrders,
                    0
                ),

                2

            ) AS AverageOrderValue,

            ROUND(

                (
                    julianday(
                        LastOrderDate
                    )
                    -
                    julianday(
                        FirstOrderDate
                    )
                )
                /
                NULLIF(
                    TotalOrders - 1,
                    0
                ),

                2

            ) AS PurchaseFrequency,

            ROUND(

                TotalSpend
                *
                (

                    (
                        julianday('now')
                        -
                        julianday(
                            FirstOrderDate
                        )
                    )

                    /

                    NULLIF(

                        julianday(
                            LastOrderDate
                        )
                        -
                        julianday(
                            FirstOrderDate
                        ),

                        0

                    )

                ),

                2

            ) AS CustomerLifetimeValue

        FROM CustomerSpend

        WHERE
            TotalOrders > 1

        ORDER BY
            CustomerLifetimeValue DESC

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


        if not df.empty:

            fig = px.bar(
                df.head(15).sort_values(
                    "CustomerLifetimeValue"
                ),
                x="CustomerLifetimeValue",
                y="CustomerKey",
                orientation="h",
                title="Top Customers by CLV"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # SEASONALITY
    # ========================================================

    with tab3:

        section_title(
            "Sales Seasonality Analysis"
        )


        query = f"""

        SELECT

            strftime(
                '%Y-%m',
                "Order Date"
            ) AS Month,

            SUM(
                "Unit Price USD"
                *
                "Quantity"
            ) AS Total_Sales

        FROM MergedData

        WHERE {WHERE_CLAUSE}

        GROUP BY
            strftime(
                '%Y-%m',
                "Order Date"
            )

        ORDER BY Month

        """

        df = execute_query(
            query,
            FILTER_PARAMS
        )


        if not df.empty:

            fig = px.line(
                df,
                x="Month",
                y="Total_Sales",
                markers=True,
                title="Sales Seasonality"
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# DATA EXPLORER
# ============================================================

elif page == "🗃️ Data Explorer":

    st.header("🗃️ Data Explorer")


    selected_table = st.selectbox(
        "Select Database Table",
        tables
    )


    st.subheader(
        f"📋 {selected_table}"
    )


    # Table structure

    with st.expander("Table Structure"):

        columns_df = get_columns(
            selected_table
        )

        st.dataframe(
            columns_df,
            use_container_width=True,
            hide_index=True
        )


    # Number of rows

    count_query = f"""

    SELECT COUNT(*) AS TotalRows
    FROM "{selected_table}"

    """

    count_df = execute_query(
        count_query
    )


    total_rows = int(
        count_df.iloc[0]["TotalRows"]
    )


    st.metric(
        "Total Rows",
        format_number(total_rows)
    )


    rows_to_display = st.slider(
        "Rows to display",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )


    query = f"""

    SELECT *

    FROM "{selected_table}"

    LIMIT ?

    """

    df = execute_query(
        query,
        (rows_to_display,)
    )


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    # Download

    csv = df.to_csv(
        index=False
    ).encode("utf-8")


    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=f"{selected_table}.csv",
        mime="text/csv"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "DataSpark | Global Electronics Analytics Dashboard"
)