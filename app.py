import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from pathlib import Path
from huggingface_hub import hf_hub_download


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="DataSpark | Global Electronics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .main {
            padding-top: 1rem;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        .metric-card {
            background: linear-gradient(135deg, #ffffff, #f5f7fb);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #e6e9ef;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            text-align: center;
        }

        .metric-title {
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 28px;
            font-weight: 700;
            color: #111827;
        }

        .section-title {
            font-size: 24px;
            font-weight: 700;
            margin-top: 20px;
            margin-bottom: 15px;
        }

        .small-text {
            color: #6b7280;
            font-size: 13px;
        }

        div[data-testid="stSidebar"] {
            border-right: 1px solid #e5e7eb;
        }

        .stDownloadButton button {
            width: 100%;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HUGGING FACE DATABASE CONFIGURATION
# ============================================================

HF_REPO_ID = "Ajmal624/dataspark-data"
DB_FILENAME = "Data_Spark.db"


@st.cache_resource
def get_database_path():
    """
    Download Data_Spark.db from Hugging Face.

    IMPORTANT:
    This repository is accessed as a normal Hugging Face repo.
    Do NOT use repo_type="dataset" here.
    """

    try:
        db_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=DB_FILENAME
        )

        return Path(db_path)

    except Exception as e:
        st.error(
            "Unable to download the DataSpark database from Hugging Face."
        )

        st.error(
            "Please check that Data_Spark.db exists in "
            "Ajmal624/dataspark-data."
        )

        st.code(str(e))

        st.stop()


DB_PATH = get_database_path()


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_connection():
    """Create SQLite database connection."""

    return sqlite3.connect(str(DB_PATH))


@st.cache_data
def get_tables():
    """Return all database tables."""

    conn = get_connection()

    try:
        query = """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """

        df = pd.read_sql_query(query, conn)

        return df["name"].tolist()

    finally:
        conn.close()


@st.cache_data
def get_columns(table_name):
    """Return columns for a table."""

    conn = get_connection()

    try:
        query = f'PRAGMA table_info("{table_name}")'

        df = pd.read_sql_query(query, conn)

        return df["name"].tolist()

    finally:
        conn.close()


def execute_query(query, params=None):
    """Execute SQL query and return DataFrame."""

    conn = get_connection()

    try:
        if params:
            return pd.read_sql_query(query, conn, params=params)

        return pd.read_sql_query(query, conn)

    except Exception as e:
        st.error(f"Database query error: {e}")
        return pd.DataFrame()

    finally:
        conn.close()


# ============================================================
# DATABASE VALIDATION
# ============================================================

tables = get_tables()

if not tables:
    st.error("No tables were found in Data_Spark.db.")
    st.stop()


# ============================================================
# FIND MAIN DATA TABLE
# ============================================================

if "MergedData" in tables:
    MAIN_TABLE = "MergedData"
else:
    # Try common variations
    possible_tables = [
        t for t in tables
        if t.lower().replace("_", "") in [
            "mergeddata",
            "merged",
            "salesdata"
        ]
    ]

    if possible_tables:
        MAIN_TABLE = possible_tables[0]
    else:
        MAIN_TABLE = tables[0]


MAIN_COLUMNS = get_columns(MAIN_TABLE)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_column(possible_names, columns=None):
    """
    Find a column using case-insensitive matching.
    """

    if columns is None:
        columns = MAIN_COLUMNS

    normalized = {
        str(col).lower().replace(" ", "").replace("_", ""): col
        for col in columns
    }

    for name in possible_names:
        key = name.lower().replace(" ", "").replace("_", "")

        if key in normalized:
            return normalized[key]

    return None


def format_number(value):
    """Format numeric values."""

    if value is None:
        return "0"

    try:
        value = float(value)

        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"

        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"

        if value >= 1_000:
            return f"{value / 1_000:.2f}K"

        return f"{value:,.0f}"

    except Exception:
        return str(value)


def format_currency(value):
    """Format currency values."""

    if value is None:
        return "$0"

    try:
        value = float(value)

        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"

        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"

        if abs(value) >= 1_000:
            return f"${value / 1_000:.2f}K"

        return f"${value:,.0f}"

    except Exception:
        return str(value)


def metric_card(title, value):
    """Display KPI card."""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# COLUMN DETECTION
# ============================================================

date_col = find_column([
    "Order Date",
    "OrderDate",
    "Date",
    "Sale Date",
    "Sales Date"
])

country_col = find_column([
    "Country",
    "CountryName"
])

category_col = find_column([
    "Category",
    "Product Category"
])

brand_col = find_column([
    "Brand"
])

gender_col = find_column([
    "Gender"
])

order_col = find_column([
    "OrderID",
    "Order ID",
    "Order"
])

customer_col = find_column([
    "CustomerKey",
    "Customer ID",
    "CustomerID",
    "Customer Key"
])

quantity_col = find_column([
    "Quantity",
    "Units",
    "Units Sold"
])

revenue_col = find_column([
    "Revenue",
    "Sales",
    "Sales Amount",
    "Total Sales"
])

profit_col = find_column([
    "Gross Profit",
    "GrossProfit",
    "Profit",
    "Gross Profit Amount"
])

product_col = find_column([
    "Product Name",
    "ProductName",
    "Product"
])

store_col = find_column([
    "Store",
    "Store Name",
    "StoreName"
])

city_col = find_column([
    "City"
])

state_col = find_column([
    "State"
])


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 DataSpark")

st.sidebar.markdown(
    """
    **Global Electronics**

    Interactive business intelligence dashboard
    """
)

st.sidebar.divider()


page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Customer Analytics",
        "Sales Analytics",
        "Product Analytics",
        "Store Analytics",
        "Advanced Analytics",
        "Data Explorer"
    ]
)


st.sidebar.divider()

st.sidebar.caption("Database")
st.sidebar.code(DB_PATH.name)

st.sidebar.caption(f"Main table: {MAIN_TABLE}")


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.subheader("🔎 Filters")


# -------------------------
# Country filter
# -------------------------

selected_country = "All"

if country_col:

    country_query = f'''
        SELECT DISTINCT "{country_col}"
        FROM "{MAIN_TABLE}"
        WHERE "{country_col}" IS NOT NULL
        ORDER BY "{country_col}"
    '''

    country_df = execute_query(country_query)

    if not country_df.empty:

        countries = country_df[country_col].dropna().astype(str).tolist()

        selected_country = st.sidebar.selectbox(
            "Country",
            ["All"] + countries
        )


# -------------------------
# Category filter
# -------------------------

selected_category = "All"

if category_col:

    category_query = f'''
        SELECT DISTINCT "{category_col}"
        FROM "{MAIN_TABLE}"
        WHERE "{category_col}" IS NOT NULL
        ORDER BY "{category_col}"
    '''

    category_df = execute_query(category_query)

    if not category_df.empty:

        categories = (
            category_df[category_col]
            .dropna()
            .astype(str)
            .tolist()
        )

        selected_category = st.sidebar.selectbox(
            "Category",
            ["All"] + categories
        )


# -------------------------
# Brand filter
# -------------------------

selected_brand = "All"

if brand_col:

    brand_query = f'''
        SELECT DISTINCT "{brand_col}"
        FROM "{MAIN_TABLE}"
        WHERE "{brand_col}" IS NOT NULL
        ORDER BY "{brand_col}"
    '''

    brand_df = execute_query(brand_query)

    if not brand_df.empty:

        brands = (
            brand_df[brand_col]
            .dropna()
            .astype(str)
            .tolist()
        )

        selected_brand = st.sidebar.selectbox(
            "Brand",
            ["All"] + brands
        )


# -------------------------
# Gender filter
# -------------------------

selected_gender = "All"

if gender_col:

    gender_query = f'''
        SELECT DISTINCT "{gender_col}"
        FROM "{MAIN_TABLE}"
        WHERE "{gender_col}" IS NOT NULL
        ORDER BY "{gender_col}"
    '''

    gender_df = execute_query(gender_query)

    if not gender_df.empty:

        genders = (
            gender_df[gender_col]
            .dropna()
            .astype(str)
            .tolist()
        )

        selected_gender = st.sidebar.selectbox(
            "Gender",
            ["All"] + genders
        )


# ============================================================
# BUILD FILTER CONDITIONS
# ============================================================

conditions = []
params = []


if country_col and selected_country != "All":

    conditions.append(
        f'"{country_col}" = ?'
    )

    params.append(selected_country)


if category_col and selected_category != "All":

    conditions.append(
        f'"{category_col}" = ?'
    )

    params.append(selected_category)


if brand_col and selected_brand != "All":

    conditions.append(
        f'"{brand_col}" = ?'
    )

    params.append(selected_brand)


if gender_col and selected_gender != "All":

    conditions.append(
        f'"{gender_col}" = ?'
    )

    params.append(selected_gender)


where_clause = ""

if conditions:
    where_clause = "WHERE " + " AND ".join(conditions)


# ============================================================
# HEADER
# ============================================================

st.title("📊 DataSpark")

st.markdown(
    """
    ### Global Electronics Business Intelligence Dashboard

    Explore customers, sales, products, stores and advanced business analytics.
    """
)

st.divider()


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    st.header("📈 Business Overview")

    # --------------------------------------------------------
    # KPI QUERY
    # --------------------------------------------------------

    kpi_query_parts = []

    if order_col:
        kpi_query_parts.append(
            f'COUNT(DISTINCT "{order_col}") AS orders'
        )
    else:
        kpi_query_parts.append(
            "COUNT(*) AS orders"
        )

    if customer_col:
        kpi_query_parts.append(
            f'COUNT(DISTINCT "{customer_col}") AS customers'
        )
    else:
        kpi_query_parts.append(
            "0 AS customers"
        )

    if quantity_col:
        kpi_query_parts.append(
            f'COALESCE(SUM("{quantity_col}"), 0) AS units'
        )
    else:
        kpi_query_parts.append(
            "0 AS units"
        )

    if revenue_col:
        kpi_query_parts.append(
            f'COALESCE(SUM("{revenue_col}"), 0) AS revenue'
        )
    else:
        kpi_query_parts.append(
            "0 AS revenue"
        )

    if profit_col:
        kpi_query_parts.append(
            f'COALESCE(SUM("{profit_col}"), 0) AS profit'
        )
    else:
        kpi_query_parts.append(
            "0 AS profit"
        )

    kpi_query = f'''
        SELECT
            {", ".join(kpi_query_parts)}
        FROM "{MAIN_TABLE}"
        {where_clause}
    '''

    kpi_df = execute_query(kpi_query, params)

    if not kpi_df.empty:

        row = kpi_df.iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            metric_card(
                "Orders",
                format_number(row["orders"])
            )

        with c2:
            metric_card(
                "Customers",
                format_number(row["customers"])
            )

        with c3:
            metric_card(
                "Units Sold",
                format_number(row["units"])
            )

        with c4:
            metric_card(
                "Revenue",
                format_currency(row["revenue"])
            )

        with c5:
            metric_card(
                "Gross Profit",
                format_currency(row["profit"])
            )

    st.divider()

    # --------------------------------------------------------
    # SALES BY COUNTRY
    # --------------------------------------------------------

    if country_col and revenue_col:

        st.subheader("🌍 Revenue by Country")

        query = f'''
            SELECT
                "{country_col}" AS Country,
                SUM("{revenue_col}") AS Revenue
            FROM "{MAIN_TABLE}"
            {where_clause}
            GROUP BY "{country_col}"
            ORDER BY Revenue DESC
        '''

        df = execute_query(query, params)

        if not df.empty:

            col1, col2 = st.columns(2)

            with col1:

                fig = px.bar(
                    df,
                    x="Country",
                    y="Revenue",
                    title="Revenue by Country"
                )

                fig.update_layout(
                    xaxis_title="Country",
                    yaxis_title="Revenue"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            with col2:

                fig = px.pie(
                    df,
                    names="Country",
                    values="Revenue",
                    title="Revenue Distribution"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


    # --------------------------------------------------------
    # REVENUE BY CATEGORY
    # --------------------------------------------------------

    if category_col and revenue_col:

        st.subheader("🛍️ Revenue by Category")

        query = f'''
            SELECT
                "{category_col}" AS Category,
                SUM("{revenue_col}") AS Revenue
            FROM "{MAIN_TABLE}"
            {where_clause}
            GROUP BY "{category_col}"
            ORDER BY Revenue DESC
        '''

        df = execute_query(query, params)

        if not df.empty:

            fig = px.bar(
                df,
                x="Category",
                y="Revenue",
                title="Revenue by Product Category"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# CUSTOMER ANALYTICS
# ============================================================

elif page == "Customer Analytics":

    st.header("👥 Customer Analytics")

    if not customer_col:

        st.warning(
            "Customer ID column was not found in the database."
        )

    else:

        # ----------------------------------------------------
        # Customer count
        # ----------------------------------------------------

        query = f'''
            SELECT
                COUNT(DISTINCT "{customer_col}") AS Customers
            FROM "{MAIN_TABLE}"
            {where_clause}
        '''

        df = execute_query(query, params)

        if not df.empty:

            metric_card(
                "Total Customers",
                format_number(df.iloc[0]["Customers"])
            )

        st.divider()

        # ----------------------------------------------------
        # Customers by country
        # ----------------------------------------------------

        if country_col:

            query = f'''
                SELECT
                    "{country_col}" AS Country,
                    COUNT(DISTINCT "{customer_col}") AS Customers
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{country_col}"
                ORDER BY Customers DESC
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.bar(
                    df,
                    x="Country",
                    y="Customers",
                    title="Customers by Country"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

        # ----------------------------------------------------
        # Gender
        # ----------------------------------------------------

        if gender_col:

            query = f'''
                SELECT
                    "{gender_col}" AS Gender,
                    COUNT(DISTINCT "{customer_col}") AS Customers
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{gender_col}"
                ORDER BY Customers DESC
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.pie(
                    df,
                    names="Gender",
                    values="Customers",
                    title="Customer Distribution by Gender"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


# ============================================================
# SALES ANALYTICS
# ============================================================

elif page == "Sales Analytics":

    st.header("💰 Sales Analytics")

    if not revenue_col:

        st.warning(
            "Revenue/Sales column was not found."
        )

    else:

        # ----------------------------------------------------
        # Total revenue
        # ----------------------------------------------------

        query = f'''
            SELECT
                SUM("{revenue_col}") AS Revenue
            FROM "{MAIN_TABLE}"
            {where_clause}
        '''

        df = execute_query(query, params)

        if not df.empty:

            metric_card(
                "Total Revenue",
                format_currency(df.iloc[0]["Revenue"])
            )

        st.divider()

        # ----------------------------------------------------
        # Sales by category
        # ----------------------------------------------------

        if category_col:

            query = f'''
                SELECT
                    "{category_col}" AS Category,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{category_col}"
                ORDER BY Revenue DESC
            '''

            df = execute_query(query, params)

            if not df.empty:

                col1, col2 = st.columns(2)

                with col1:

                    fig = px.bar(
                        df,
                        x="Category",
                        y="Revenue",
                        title="Revenue by Category"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                with col2:

                    fig = px.pie(
                        df,
                        names="Category",
                        values="Revenue",
                        title="Revenue Distribution"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

        # ----------------------------------------------------
        # Sales by brand
        # ----------------------------------------------------

        if brand_col:

            query = f'''
                SELECT
                    "{brand_col}" AS Brand,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{brand_col}"
                ORDER BY Revenue DESC
                LIMIT 20
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.bar(
                    df,
                    x="Brand",
                    y="Revenue",
                    title="Top Brands by Revenue"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

        # ----------------------------------------------------
        # Revenue trend
        # ----------------------------------------------------

        if date_col:

            query = f'''
                SELECT
                    DATE("{date_col}") AS Date,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY DATE("{date_col}")
                ORDER BY Date
            '''

            df = execute_query(query, params)

            if not df.empty:

                df["Date"] = pd.to_datetime(
                    df["Date"],
                    errors="coerce"
                )

                df = df.dropna(subset=["Date"])

                if not df.empty:

                    fig = px.line(
                        df,
                        x="Date",
                        y="Revenue",
                        title="Revenue Trend"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )


# ============================================================
# PRODUCT ANALYTICS
# ============================================================

elif page == "Product Analytics":

    st.header("📦 Product Analytics")

    if not product_col:

        st.warning(
            "Product column was not found in the database."
        )

    else:

        # ----------------------------------------------------
        # Product count
        # ----------------------------------------------------

        query = f'''
            SELECT
                COUNT(DISTINCT "{product_col}") AS Products
            FROM "{MAIN_TABLE}"
            {where_clause}
        '''

        df = execute_query(query, params)

        if not df.empty:

            metric_card(
                "Products",
                format_number(df.iloc[0]["Products"])
            )

        st.divider()

        # ----------------------------------------------------
        # Product revenue
        # ----------------------------------------------------

        if revenue_col:

            query = f'''
                SELECT
                    "{product_col}" AS Product,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{product_col}"
                ORDER BY Revenue DESC
                LIMIT 20
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.bar(
                    df,
                    x="Revenue",
                    y="Product",
                    orientation="h",
                    title="Top Products by Revenue"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

        # ----------------------------------------------------
        # Category analysis
        # ----------------------------------------------------

        if category_col and revenue_col:

            query = f'''
                SELECT
                    "{category_col}" AS Category,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{category_col}"
                ORDER BY Revenue DESC
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.pie(
                    df,
                    names="Category",
                    values="Revenue",
                    title="Category Revenue Distribution"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


# ============================================================
# STORE ANALYTICS
# ============================================================

elif page == "Store Analytics":

    st.header("🏪 Store Analytics")

    if not store_col:

        st.warning(
            "Store column was not found in the database."
        )

    else:

        # ----------------------------------------------------
        # Store count
        # ----------------------------------------------------

        query = f'''
            SELECT
                COUNT(DISTINCT "{store_col}") AS Stores
            FROM "{MAIN_TABLE}"
            {where_clause}
        '''

        df = execute_query(query, params)

        if not df.empty:

            metric_card(
                "Stores",
                format_number(df.iloc[0]["Stores"])
            )

        st.divider()

        # ----------------------------------------------------
        # Store revenue
        # ----------------------------------------------------

        if revenue_col:

            query = f'''
                SELECT
                    "{store_col}" AS Store,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{store_col}"
                ORDER BY Revenue DESC
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.bar(
                    df,
                    x="Store",
                    y="Revenue",
                    title="Revenue by Store"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

        # ----------------------------------------------------
        # City
        # ----------------------------------------------------

        if city_col and revenue_col:

            query = f'''
                SELECT
                    "{city_col}" AS City,
                    SUM("{revenue_col}") AS Revenue
                FROM "{MAIN_TABLE}"
                {where_clause}
                GROUP BY "{city_col}"
                ORDER BY Revenue DESC
                LIMIT 20
            '''

            df = execute_query(query, params)

            if not df.empty:

                fig = px.bar(
                    df,
                    x="City",
                    y="Revenue",
                    title="Top Cities by Revenue"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )


# ============================================================
# ADVANCED ANALYTICS
# ============================================================

elif page == "Advanced Analytics":

    st.header("🧠 Advanced Analytics")

    st.markdown(
        "Explore deeper relationships in the sales data."
    )

    # --------------------------------------------------------
    # Brand + Category
    # --------------------------------------------------------

    if brand_col and category_col and revenue_col:

        st.subheader("Brand × Category Performance")

        query = f'''
            SELECT
                "{brand_col}" AS Brand,
                "{category_col}" AS Category,
                SUM("{revenue_col}") AS Revenue
            FROM "{MAIN_TABLE}"
            {where_clause}
            GROUP BY
                "{brand_col}",
                "{category_col}"
            ORDER BY Revenue DESC
        '''

        df = execute_query(query, params)

        if not df.empty:

            fig = px.treemap(
                df,
                path=["Category", "Brand"],
                values="Revenue",
                title="Revenue Treemap"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # --------------------------------------------------------
    # Profit analysis
    # --------------------------------------------------------

    if revenue_col and profit_col:

        st.subheader("Revenue vs Gross Profit")

        query = f'''
            SELECT
                SUM("{revenue_col}") AS Revenue,
                SUM("{profit_col}") AS Profit
            FROM "{MAIN_TABLE}"
            {where_clause}
        '''

        df = execute_query(query, params)

        if not df.empty:

            revenue = df.iloc[0]["Revenue"]
            profit = df.iloc[0]["Profit"]

            if revenue and revenue != 0:

                margin = (profit / revenue) * 100

                c1, c2, c3 = st.columns(3)

                with c1:
                    metric_card(
                        "Revenue",
                        format_currency(revenue)
                    )

                with c2:
                    metric_card(
                        "Gross Profit",
                        format_currency(profit)
                    )

                with c3:
                    metric_card(
                        "Profit Margin",
                        f"{margin:.2f}%"
                    )

    # --------------------------------------------------------
    # Quantity analysis
    # --------------------------------------------------------

    if quantity_col and category_col:

        st.subheader("Units Sold by Category")

        query = f'''
            SELECT
                "{category_col}" AS Category,
                SUM("{quantity_col}") AS Units
            FROM "{MAIN_TABLE}"
            {where_clause}
            GROUP BY "{category_col}"
            ORDER BY Units DESC
        '''

        df = execute_query(query, params)

        if not df.empty:

            fig = px.bar(
                df,
                x="Category",
                y="Units",
                title="Units Sold by Category"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # --------------------------------------------------------
    # Country / category matrix
    # --------------------------------------------------------

    if country_col and category_col and revenue_col:

        st.subheader("Country × Category Revenue")

        query = f'''
            SELECT
                "{country_col}" AS Country,
                "{category_col}" AS Category,
                SUM("{revenue_col}") AS Revenue
            FROM "{MAIN_TABLE}"
            {where_clause}
            GROUP BY
                "{country_col}",
                "{category_col}"
        '''

        df = execute_query(query, params)

        if not df.empty:

            pivot = df.pivot_table(
                index="Country",
                columns="Category",
                values="Revenue",
                aggfunc="sum",
                fill_value=0
            )

            st.dataframe(
                pivot,
                use_container_width=True
            )


# ============================================================
# DATA EXPLORER
# ============================================================

elif page == "Data Explorer":

    st.header("🔍 Data Explorer")

    st.markdown(
        "Inspect the SQLite database tables and export data."
    )

    # --------------------------------------------------------
    # Table selector
    # --------------------------------------------------------

    selected_table = st.selectbox(
        "Select Table",
        tables
    )

    if selected_table:

        columns = get_columns(selected_table)

        st.subheader("Table Information")

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "Number of Columns",
                len(columns)
            )

        with c2:

            count_query = f'''
                SELECT COUNT(*) AS count
                FROM "{selected_table}"
            '''

            count_df = execute_query(count_query)

            row_count = (
                int(count_df.iloc[0]["count"])
                if not count_df.empty
                else 0
            )

            st.metric(
                "Number of Rows",
                f"{row_count:,}"
            )

        st.divider()

        # ----------------------------------------------------
        # Schema
        # ----------------------------------------------------

        st.subheader("📋 Table Schema")

        schema_query = f'''
            PRAGMA table_info("{selected_table}")
        '''

        schema_df = execute_query(schema_query)

        if not schema_df.empty:

            st.dataframe(
                schema_df,
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # ----------------------------------------------------
        # Data preview
        # ----------------------------------------------------

        st.subheader("👀 Data Preview")

        preview_rows = st.slider(
            "Rows to display",
            min_value=10,
            max_value=500,
            value=100,
            step=10
        )

        preview_query = f'''
            SELECT *
            FROM "{selected_table}"
            LIMIT {preview_rows}
        '''

        preview_df = execute_query(preview_query)

        if not preview_df.empty:

            st.dataframe(
                preview_df,
                use_container_width=True,
                hide_index=True
            )

            # ------------------------------------------------
            # CSV download
            # ------------------------------------------------

            csv_data = preview_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                label="⬇️ Download Preview as CSV",
                data=csv_data,
                file_name=f"{selected_table}_preview.csv",
                mime="text/csv"
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center;">
        <p class="small-text">
            📊 DataSpark | Global Electronics Business Intelligence Dashboard
        </p>
        <p class="small-text">
            Built with Streamlit, Pandas, Plotly, SQLite & Hugging Face
        </p>
    </div>
    """,
    unsafe_allow_html=True
)