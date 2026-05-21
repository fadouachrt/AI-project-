# # # import sys
# # # import os
# # # import json
# # # import traceback
# # # from fastapi import FastAPI, Query
# # # from fastapi.staticfiles import StaticFiles
# # # from fastapi.responses import HTMLResponse, JSONResponse
# # # from fastapi.middleware.cors import CORSMiddleware
# # # import uvicorn

# # # sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# # # from runner import ALGO_RUNNERS, get_team_meta, get_all_teams, get_derby_set

# # # app = FastAPI(title="Sport League Scheduler API")

# # # # CORS for local development
# # # app.add_middleware(
# # #     CORSMiddleware,
# # #     allow_origins=["*"],
# # #     allow_credentials=True,
# # #     allow_methods=["*"],
# # #     allow_headers=["*"],
# # # )

# # # # Serve static files (images)
# # # app.mount("/images", StaticFiles(directory="images"), name="images")
# # # # Serve the main HTML (we'll embed it directly, no separate static folder)
# # # # But for flexibility, we'll mount a static folder if you want to serve additional assets.
# # # # However, we'll serve the HTML from a file in the same directory.
# # # # Create a "static" folder and put index.html there.
# # # app.mount("/static", StaticFiles(directory="static"), name="static")

# # # @app.get("/", response_class=HTMLResponse)
# # # async def root():
# # #     # If you want to serve the HTML directly without a separate file, you can embed it here.
# # #     # But for clarity, we read from static/index.html
# # #     with open("static/index.html", "r", encoding="utf-8") as f:
# # #         return HTMLResponse(content=f.read())

# # # @app.get("/api/teams")
# # # async def get_teams(n_teams: int = Query(10, ge=4, le=16, step=2)):
# # #     all_teams = [t.name for t in get_all_teams()]
# # #     teams_slice = all_teams[:n_teams]
# # #     team_meta = get_team_meta()
# # #     derby_set = get_derby_set()
# # #     result = []
# # #     for name in teams_slice:
# # #         meta = team_meta.get(name, {})
# # #         result.append({
# # #             "name": name,
# # #             "city": meta.get("city", "").title(),
# # #             "stadium": meta.get("stadium", ""),
# # #             "lat": meta.get("lat", 0),
# # #             "lon": meta.get("lon", 0),
# # #             "derby": any(name in p for p in derby_set),
# # #         })
# # #     return JSONResponse(content=result)

# # # @app.get("/api/run/{algorithm}")
# # # async def run_algorithm(algorithm: str, n_teams: int = Query(10, ge=4, le=16, step=2)):
# # #     # Map display name to backend key if needed
# # #     display_to_key = {
# # #         "Greedy Search": "greedy",
# # #         "Hill Climbing": "hill_climbing",
# # #         "Simulated Annealing": "simulated_annealing",
# # #         "CSP": "csp"
# # #     }
# # #     algo_key = algorithm if algorithm in ALGO_RUNNERS else display_to_key.get(algorithm)
# # #     if not algo_key or algo_key not in ALGO_RUNNERS:
# # #         return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})
    
# # #     try:
# # #         sched_display, stats, elapsed = ALGO_RUNNERS[algo_key](n_teams)
# # #         return JSONResponse(content={
# # #             "schedule": sched_display,
# # #             "stats": stats,
# # #             "elapsed": elapsed,
# # #         })
# # #     except Exception as e:
# # #         traceback.print_exc()
# # #         return JSONResponse(status_code=500, content={"error": str(e)})

# # # if __name__ == "__main__":
# # #     uvicorn.run(app, host="0.0.0.0", port=8000)

# # import sys
# # import os
# # import json
# # import traceback
# # from fastapi import FastAPI, Query
# # from fastapi.staticfiles import StaticFiles
# # from fastapi.responses import HTMLResponse, JSONResponse
# # from fastapi.middleware.cors import CORSMiddleware
# # import uvicorn

# # # Add current directory to path so runner can be imported
# # sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# # from runner import ALGO_RUNNERS, get_team_meta, get_all_teams, get_derby_set

# # app = FastAPI(title="Sport League Scheduler API")

# # # Allow all origins (for development)
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # # Serve static files (images and HTML)
# # # The HTML will be served from the "static" folder
# # app.mount("/static", StaticFiles(directory="static"), name="static")
# # # Also mount images folder at root for easier access (if images are in root/images)
# # if os.path.exists("images"):
# #     app.mount("/images", StaticFiles(directory="images"), name="images")

# # @app.get("/", response_class=HTMLResponse)
# # async def root():
# #     # Serve the main HTML from static folder
# #     with open("static/index.html", "r", encoding="utf-8") as f:
# #         return HTMLResponse(content=f.read())

# # @app.get("/api/teams")
# # async def get_teams(n_teams: int = Query(10, ge=4, le=16, step=2)):
# #     """Return list of teams with metadata."""
# #     all_teams = [t.name for t in get_all_teams()]
# #     teams_slice = all_teams[:n_teams]
# #     team_meta = get_team_meta()
# #     derby_set = get_derby_set()
# #     result = []
# #     for name in teams_slice:
# #         meta = team_meta.get(name, {})
# #         result.append({
# #             "name": name,
# #             "city": meta.get("city", "").title(),
# #             "stadium": meta.get("stadium", ""),
# #             "lat": meta.get("lat", 0),
# #             "lon": meta.get("lon", 0),
# #             "derby": any(name in p for p in derby_set),
# #         })
# #     return JSONResponse(content=result)

# # @app.get("/api/run/{algorithm}")
# # async def run_algorithm(algorithm: str, n_teams: int = Query(10, ge=4, le=16, step=2)):
# #     """Run selected algorithm and return schedule + stats."""
# #     # Map display name to backend key if needed
# #     display_to_key = {
# #         "Greedy Search": "greedy",
# #         "Hill Climbing": "hill_climbing",
# #         "Simulated Annealing": "simulated_annealing",
# #         "CSP": "csp"
# #     }
# #     algo_key = algorithm if algorithm in ALGO_RUNNERS else display_to_key.get(algorithm)
# #     if not algo_key or algo_key not in ALGO_RUNNERS:
# #         return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})
    
# #     try:
# #         sched_display, stats, elapsed = ALGO_RUNNERS[algo_key](n_teams)
# #         return JSONResponse(content={
# #             "schedule": sched_display,
# #             "stats": stats,
# #             "elapsed": elapsed,
# #         })
# #     except Exception as e:
# #         traceback.print_exc()
# #         return JSONResponse(status_code=500, content={"error": str(e)})

# # if __name__ == "__main__":
# #     # Run on 0.0.0.0 so it's accessible from network, port 8000
# #     uvicorn.run(app, host="0.0.0.0", port=8000)
# import sys
# import os
# import json
# import traceback
# from fastapi import FastAPI, Query
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import HTMLResponse, JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import uvicorn

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from runner import ALGO_RUNNERS, get_team_meta, get_all_teams, get_derby_set

# app = FastAPI(title="Sport League Scheduler API")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.mount("/static", StaticFiles(directory="static"), name="static")
# if os.path.exists("images"):
#     app.mount("/images", StaticFiles(directory="images"), name="images")

# @app.get("/", response_class=HTMLResponse)
# async def root():
#     with open("static/index.html", "r", encoding="utf-8") as f:
#         return HTMLResponse(content=f.read())

# @app.get("/api/teams")
# async def get_teams(n_teams: int = Query(10, ge=4, le=16)):
#     """Return list of teams with metadata."""
#     all_teams = [t.name for t in get_all_teams()]
#     teams_slice = all_teams[:n_teams]
#     team_meta = get_team_meta()
#     derby_set = get_derby_set()
#     result = []
#     for name in teams_slice:
#         meta = team_meta.get(name, {})
#         result.append({
#             "name":    name,
#             "city":    meta.get("city", "").title(),
#             "stadium": meta.get("stadium", ""),
#             "lat":     meta.get("lat", 0),
#             "lon":     meta.get("lon", 0),
#             "derby":   any(name in p for p in derby_set),
#         })
#     return JSONResponse(content=result)

# @app.get("/api/run/{algorithm}")
# async def run_algorithm(algorithm: str, n_teams: int = Query(10, ge=4, le=16)):
#     """Run selected algorithm and return schedule + stats."""
#     display_to_key = {
#         "Greedy Search":      "greedy",
#         "Hill Climbing":      "hill_climbing",
#         "Simulated Annealing":"simulated_annealing",
#         "CSP":                "csp",
#     }
#     algo_key = algorithm if algorithm in ALGO_RUNNERS else display_to_key.get(algorithm)
#     if not algo_key or algo_key not in ALGO_RUNNERS:
#         return JSONResponse(status_code=400, content={"error": f"Unknown algorithm: {algorithm}"})

#     try:
#         # All runners are now async — must be awaited
#         sched_display, stats, elapsed = await ALGO_RUNNERS[algo_key](n_teams)
#         stats["elapsed"] = elapsed
#         return JSONResponse(content={
#             "schedule": sched_display,
#             "stats":    stats,
#             "elapsed":  elapsed,
#         })
#     except Exception as e:
#         traceback.print_exc()
#         return JSONResponse(status_code=500, content={"error": str(e)})

# @app.get("/api/test_all")
# async def test_all_team_counts():
#     """Quick health-check: run Hill Climbing for every valid team count."""
#     from runner import run_hill_climbing
#     results = {}
#     for n in [4, 6, 8, 10, 12, 14, 16]:
#         try:
#             sched, stats, elapsed = await run_hill_climbing(n)
#             results[n] = {"ok": True, "rounds": len(sched), "elapsed": round(elapsed, 3)}
#         except Exception as e:
#             results[n] = {"ok": False, "error": str(e)}
#     return results

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)

import sys
import os
import json
import traceback
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runner import ALGO_RUNNERS, get_team_meta, get_all_teams, get_derby_set

app = FastAPI(title="Sport League Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("images"):
    app.mount("/images", StaticFiles(directory="images"), name="images")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/teams")
async def get_teams(n_teams: int = Query(10, ge=4, le=16)):
    """Return list of teams with metadata."""
    all_teams = [t.name for t in get_all_teams()]
    teams_slice = all_teams[:n_teams]
    team_meta = get_team_meta()
    derby_set = get_derby_set()
    result = []
    for name in teams_slice:
        meta = team_meta.get(name, {})
        result.append({
            "name":    name,
            "city":    meta.get("city", "").title(),
            "stadium": meta.get("stadium", ""),
            "lat":     meta.get("lat", 0),
            "lon":     meta.get("lon", 0),
            "derby":   any(name in p for p in derby_set),
        })
    return JSONResponse(content=result)

@app.get("/api/run/{algorithm}")
async def run_algorithm(algorithm: str, n_teams: int = Query(10, ge=4, le=16)):
    """
    Run the selected algorithm and return schedule + stats.
    On failure, returns HTTP 200 with schedule=null and an error field
    so the frontend can display a per-algo error without aborting the whole run loop.
    """
    display_to_key = {
        "Greedy Search":       "greedy",
        "Hill Climbing":       "hill_climbing",
        "Simulated Annealing": "simulated_annealing",
        "CSP":                 "csp",
    }
    algo_key = algorithm if algorithm in ALGO_RUNNERS else display_to_key.get(algorithm)
    if not algo_key or algo_key not in ALGO_RUNNERS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown algorithm: {algorithm}"}
        )

    try:
        sched_display, stats, elapsed = await ALGO_RUNNERS[algo_key](n_teams)
        if stats:
            stats["elapsed"] = elapsed
        return JSONResponse(content={
            "schedule": sched_display,
            "stats":    stats,
            "elapsed":  elapsed,
        })
    except Exception as e:
        traceback.print_exc()
        # Return 200 so the frontend run-loop continues to the next algo
        return JSONResponse(
            status_code=200,
            content={
                "schedule": None,
                "stats":    None,
                "elapsed":  None,
                "error":    str(e),
            }
        )

@app.get("/api/test_all")
async def test_all_team_counts():
    """Quick health-check: run Hill Climbing for every valid team count."""
    from runner import run_hill_climbing
    results = {}
    for n in [4, 6, 8, 10, 12, 14, 16]:
        try:
            sched, stats, elapsed = await run_hill_climbing(n)
            results[n] = {"ok": True, "rounds": len(sched), "elapsed": round(elapsed, 3)}
        except Exception as e:
            results[n] = {"ok": False, "error": str(e)}
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)