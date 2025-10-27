from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, session
import pandas as pd
import io
import os
from queries_list import one_word_list, two_word_list, three_word_list, synonym_for_one_word, synonym_for_two_word, synonym_for_three_word
import uuid
from cachetools import TTLCache
from helper import (
    validate_csv_columns, add_tracking_columns, get_display_dataframe, 
    process_episode_data, update_query_list, generate_download_filename
)

CACHETOOLS_AVAILABLE = True

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_dev_only')

# Create a TTL cache: maxsize=100 means it can hold up to 100 users' data at once - ttl=14400 means each user's data lives for 4 hours (14400 seconds)
if CACHETOOLS_AVAILABLE:
    user_data = TTLCache(maxsize=100, ttl=14400)
else:
    user_data = {}  # Fallback: simple dict with manual cleanup


def get_user_id():
    """Assign or retrieve a unique session ID for each user."""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


def get_user_data(user_id: str | None = None):
    """Get the user's full data dict (or empty if not set).
    If user_id is provided, use it. Otherwise, use the session-bound id.
    """
    uid = user_id or get_user_id()
    return user_data.get(uid, {})


def save_user_data(new_data: dict, user_id: str | None = None):
    """Update or overwrite per-user data and refresh TTL.
    If user_id is provided, use it. Otherwise, use the session-bound id.
    """
    uid = user_id or get_user_id()
    data = user_data.get(uid, {})
    data.update(new_data)
    user_data[uid] = data  # refresh TTL


# HOME PAGE
@app.route("/", methods=["GET", "POST"])
def home():
    message = None
    table_html = None

    if request.method == "POST":
        try:
            file = request.files.get("file")
            if file and file.filename.endswith(".csv"):
                df = pd.read_csv(file)
                uploaded_filename = file.filename

                # Validate required columns
                is_valid, error_msg = validate_csv_columns(df)
                if not is_valid:
                    message = error_msg
                    return render_template("home.html", rows=None, cols=None, filename=None, message=message, table=None)

                # Add tracking columns if missing
                df = add_tracking_columns(df)

                message = "CSV uploaded successfully. Click 'Generate Important Queries' to continue."

                # Save all user-specific data in cache
                save_user_data({
                    "df": df,
                    "uploaded_filename": uploaded_filename,
                    "current_csv_file": uploaded_filename,
                    "processing_state": {}
                })
            else:
                message = "Please upload a valid CSV file."
        except Exception as e:
            message = f"Error processing CSV file: {str(e)}"
            return render_template("home.html", rows=None, cols=None, filename=None, message=message, table=None)

    # Retrieve user's DataFrame if exists
    user = get_user_data()
    df = user.get("df")
    uploaded_filename = user.get("uploaded_filename")

    # If a CSV is already uploaded, render the table with only specific columns
    if df is not None:
        display_df = get_display_dataframe(df)
        table_html = display_df.to_html(classes="table table-striped", index=False)
        
        # Get all columns and displayed columns for template
        all_columns = df.columns.tolist()
        displayed_columns = display_df.columns.tolist()
    else:
        all_columns = None
        displayed_columns = None

    rows = df.shape[0] if df is not None else None
    cols = df.shape[1] if df is not None else None

    return render_template("home.html",
                           rows=rows,
                           cols=cols,
                           filename=uploaded_filename,
                           message=message,
                           table=table_html,
                           all_columns=all_columns,
                           displayed_columns=displayed_columns)


# RESULTS PAGE - FULL PAGE
@app.route("/results", methods=["GET", "POST"])
def results():
    try:
        user = get_user_data()
        df = user.get("df")
        
        if df is None:
            return render_template(
                "results.html",
                message="Processing not done yet. Please upload a CSV first.",
                download_ready=False,
                analyzed_count=0,
                total_episodes=0
            )
    except Exception as e:
        return render_template(
            "results.html",
            message=f"Error loading results: {str(e)}",
            download_ready=False,
            analyzed_count=0,
            total_episodes=0
        )

    # Compute analyzed and total counts
    try:
        analyzed_count = int(df["Analyzed"].sum()) if "Analyzed" in df.columns else 0
    except Exception:
        analyzed_count = 0
    total_episodes = int(df.shape[0])

    # POST: when user clicks "Get Suggestions" button
    if request.method == "POST":
        title = request.form.get("title")
        if not title or title not in df["Title"].values:
            return render_template(
                "results.html",
                titles=df["Title"].tolist(),
                download_ready=("Important Words" in df.columns),
                analyzed_count=analyzed_count,
                total_episodes=total_episodes
            )

        row = df[df["Title"] == title].iloc[0]

        # Process episode data using helper function
        episode_data = process_episode_data(row)

        titles_with_index = [(i + 1, t) for i, t in enumerate(df["Title"].tolist())]
        true_count = df['Analyzed'].sum()

        return render_template(
            "results.html",
            titles=titles_with_index,
            selected_title=title,
            no_of_episodes_analysed=true_count,
            one_word=episode_data['one_word'],
            two_word=episode_data['two_word'],
            three_word=episode_data['three_word'],
            one_word_podcasts=episode_data['one_word_podcasts'],
            two_word_podcasts=episode_data['two_word_podcasts'],
            three_word_podcasts=episode_data['three_word_podcasts'],
            red_one_word=one_word_list,
            red_two_word=two_word_list,
            red_three_word=three_word_list,
            yellow_one_word=synonym_for_one_word,
            yellow_two_word=synonym_for_two_word,
            yellow_three_word=synonym_for_three_word,
            one_word_podcast_text=episode_data['one_word_text'],
            two_word_podcast_text=episode_data['two_word_text'],
            three_word_podcast_text=episode_data['three_word_text'],
            download_ready=True,
            episode_analyzed=row.get("Analyzed", False),
            queries_count=row.get("No of Queries", 0),
            analyzed_count=analyzed_count,
            total_episodes=total_episodes
        )

    # GET: base page (initial load, no suggestions yet)
    return render_template(
        "results.html",
        titles=df["Title"].tolist(),
        download_ready=("Important Words" in df.columns),
        analyzed_count=analyzed_count,
        total_episodes=total_episodes
    )


@app.route("/get_suggestions", methods=["POST"])
def get_suggestions():
    try:
        # Retrieve per-user data
        user = get_user_data()
        df = user.get("df")

        if df is None:
            return jsonify({"success": False, "error": "No CSV uploaded yet."})

        title = request.form.get("title")
        if not title or title not in df["Title"].values:
            return jsonify({"success": False, "error": "Invalid title"})
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to get suggestions: {str(e)}"})

    row = df[df["Title"] == title].iloc[0]

    # Process episode data using helper function
    episode_data = process_episode_data(row)

    # Render partial templates
    suggestions_and_planner_HTML = render_template(
        "partials/suggestions_and_planner.html",
        selected_title=title,
        one_word=episode_data['one_word'],
        two_word=episode_data['two_word'],
        three_word=episode_data['three_word'],
        one_word_podcasts=episode_data['one_word_podcasts'],
        two_word_podcasts=episode_data['two_word_podcasts'],
        three_word_podcasts=episode_data['three_word_podcasts'],
        red_one_word=one_word_list, 
        red_two_word=two_word_list,
        red_three_word=three_word_list,
        yellow_one_word=synonym_for_one_word,
        yellow_two_word=synonym_for_two_word,
        yellow_three_word=synonym_for_three_word,
        one_word_podcast_text=episode_data['one_word_text'],
        two_word_podcast_text=episode_data['two_word_text'],
        three_word_podcast_text=episode_data['three_word_text']
    )

    return jsonify({"success": True, "html": suggestions_and_planner_HTML})


# MARK EPISODE ANALYZED
@app.route("/mark_episode_analyzed", methods=["POST"])
def mark_episode_analyzed():
    user = get_user_data()
    df = user.get("df")

    if df is None:
        return jsonify({"success": False, "error": "No CSV uploaded yet."}), 400

    data = request.get_json() or {}
    title = data.get("title")
    explicit_value = data.get("value")

    if title not in df["Title"].values:
        return jsonify({"success": False, "error": "Invalid title"}), 400

    # Toggle if explicit value not provided
    if explicit_value is None:
        current = bool(df.loc[df["Title"] == title, "Analyzed"].values[0])
        new_val = not current
    else:
        new_val = bool(explicit_value)

    df.loc[df["Title"] == title, "Analyzed"] = new_val

    # Save updated DataFrame back to cache
    save_user_data({"df": df})

    return jsonify({"success": True, "Analyzed": new_val})


# ADD QUERY
@app.route("/add_query", methods=["POST"])
def add_query():
    # Retrieve per-user data
    user = get_user_data()
    df = user.get("df")

    if df is None:
        return jsonify({"success": False, "error": "No CSV uploaded yet."}), 400

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    query = (data.get("query") or "").strip()

    if not title or not query or title not in df["Title"].values:
        return jsonify({"success": False, "error": "Invalid title or query"}), 400

    # Ensure tracking columns exist
    if "No of Queries" not in df.columns:
        df["No of Queries"] = 0
    if "Added Queries" not in df.columns:
        df["Added Queries"] = ""

    existing_raw = df.loc[df["Title"] == title, "Added Queries"].values[0]
    items = update_query_list(existing_raw, query, add=True)

    # Update DataFrame
    df.loc[df["Title"] == title, "Added Queries"] = ",".join(items)
    df.loc[df["Title"] == title, "No of Queries"] = len(items)

    # Save updated DataFrame back to cache
    save_user_data({"df": df})

    return jsonify({"success": True, "saved_count": len(items), "saved_queries": items})


# REMOVE QUERY
@app.route("/remove_query", methods=["POST"])
def remove_query():
    # Retrieve per-user data
    user = get_user_data()
    df = user.get("df")

    if df is None:
        return jsonify({"success": False, "error": "No CSV uploaded yet."}), 400

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    query = (data.get("query") or "").strip()

    if not title or not query or title not in df["Title"].values:
        return jsonify({"success": False, "error": "Invalid title or query"}), 400

    existing_raw = df.loc[df["Title"] == title, "Added Queries"].values[0]
    items = update_query_list(existing_raw, query, add=False)

    # Update DataFrame
    df.loc[df["Title"] == title, "Added Queries"] = ",".join(items)
    df.loc[df["Title"] == title, "No of Queries"] = len(items)

    # Save updated DataFrame back to cache
    save_user_data({"df": df})

    return jsonify({"success": True, "saved_count": len(items), "saved_queries": items})


# GET EPISODE STATUS
@app.route("/get_episode_status")
def get_episode_status():
    # Retrieve per-user data
    user = get_user_data()
    df = user.get("df")

    if df is None:
        return jsonify({"Analyzed": False, "saved_count": 0, "saved_queries": []})

    title = request.args.get("title")
    if not title or title not in df["Title"].values:
        return jsonify({"Analyzed": False, "saved_count": 0, "saved_queries": []})

    row = df[df["Title"] == title].iloc[0]

    # Get raw value and guard against NaN / non-string
    existing_raw = row.get("Added Queries", "")
    items = update_query_list(existing_raw, "", add=False)  # Just parse existing

    return jsonify({
        "Analyzed": bool(row.get("Analyzed", False)),
        "saved_count": len(items),
        "saved_queries": items
    })


# GET ANALYSIS STATUS OVERVIEW
@app.route("/get_analysis_status")
def get_analysis_status():
    # Retrieve per-user data
    user = get_user_data()
    df = user.get("df")

    if df is None:
        return jsonify({"error": "No data available"}), 400

    # Get analyzed and not analyzed episode indices
    analyzed_indices = df.index[df.get("Analyzed", False) == True].tolist()
    not_analyzed_indices = df.index[df.get("Analyzed", False) == False].tolist()

    # Convert 0-based indices to 1-based for display
    analyzed_episodes = [str(i + 1) for i in analyzed_indices]
    not_analyzed_episodes = [str(i + 1) for i in not_analyzed_indices]

    return jsonify({
        "analyzed_episodes": analyzed_episodes,
        "not_analyzed_episodes": not_analyzed_episodes,
        "total_episodes": len(df),
        "analyzed_count": len(analyzed_episodes),
        "not_analyzed_count": len(not_analyzed_episodes)
    })


# DOWNLOAD
@app.route("/download", methods=["GET"])
def download():
    # Retrieve per-user data
    user = get_user_data()
    df = user.get("df")
    uploaded_filename = user.get("uploaded_filename")

    if df is None or uploaded_filename is None:
        return redirect(url_for("home"))

    # Generate descriptive filename
    download_name = generate_download_filename(uploaded_filename, df)

    # Prepare CSV for download
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )


# RUN APP

if __name__ == "__main__":
    app.run(debug=True, threaded=True)


    