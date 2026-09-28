import { useEffect, useRef, useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE = "https://satark-xz7b.onrender.com";

// ============================================================
// TARGET WATCHLIST
// ============================================================

function TargetWatchlist() {
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const loadTargets = async () => {
    try {
      setLoading(true);

      const response = await axios.get("/api/targets/list");

      if (response.data.success) {
        setTargets(response.data.targets || []);
      }
    } catch (error) {
      console.error("Target list error:", error);
      setMessage("Unable to load target watchlist.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTargets();
  }, []);

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setUploading(true);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(
        "/api/targets/upload",
        formData
      );

      if (response.data.success) {
        setMessage("Target profile created successfully.");

        await loadTargets();
      } else {
        setMessage(
          response.data.message || "Target upload failed."
        );
      }
    } catch (error) {
      console.error("Target upload error:", error);

      const serverMessage =
        error.response?.data?.message ||
        "Unable to create target profile.";

      setMessage(serverMessage);
    } finally {
      setUploading(false);

      event.target.value = "";
    }
  };

  return (
    <section className="watchlist-section">

      <div className="section-heading-row">

        <div>
          <div className="section-kicker">
            AUTHORIZED WATCHLIST
          </div>

          <h2>TARGET WATCHLIST</h2>

          <p>
            Manage authorized watchlist profiles used for
            candidate detection and human review.
          </p>
        </div>

        <label className="add-target-button">

          {uploading ? "PROCESSING..." : "+ ADD TARGET"}

          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleUpload}
            disabled={uploading}
            hidden
          />

        </label>

      </div>

      {message && (
        <div className="watchlist-message">
          {message}
        </div>
      )}

      {loading ? (

        <div className="watchlist-empty">
          LOADING WATCHLIST...
        </div>

      ) : targets.length === 0 ? (

        <div className="watchlist-empty">
          NO AUTHORIZED TARGET PROFILES
        </div>

      ) : (

        <div className="target-grid">

          {targets.map((target) => (

            <div
              className="target-card"
              key={target.target_id}
            >

              <div className="target-image-wrapper">

                <img
                  src={target.image}
                  alt="Authorized target profile"
                  className="target-image"
                />

                <div className="target-status">
                  <span className="status-dot"></span>
                  ACTIVE
                </div>

              </div>

              <div className="target-info">

                <div className="target-label">
                  TARGET PROFILE
                </div>

                <div className="target-id">
                  {target.target_id}
                </div>

                <div className="target-ready">
                  FACE PROFILE READY
                </div>

              </div>

            </div>

          ))}

        </div>

      )}

    </section>
  );
}

/* ============================================================
   MAIN APP
============================================================ */

function App() {
  const [backendStatus, setBackendStatus] = useState("CHECKING");
  const [aiStatus, setAiStatus] = useState("CHECKING");
  const [mobileStatus, setMobileStatus] = useState("WAITING");

  const [mobileFrame, setMobileFrame] = useState(
    `${API_BASE}/api/mobile/latest`
  );

  /* ============================================================
     AI ANALYSIS STATE
  ============================================================ */

  const [aiAnalysis, setAiAnalysis] = useState({
    status: "WAITING",
    camera: "MOBILE-01",
    faces_detected: 0,
    candidate_target_id: null,
    similarity_score: 0,
    human_review_required: false,
    timestamp: null,
  });

  /* ============================================================
     GPS STATE
  ============================================================ */

  const [locationData, setLocationData] = useState({
    latitude: null,
    longitude: null,
    accuracy_m: null,
    updated_at: null,
    camera: "MOBILE-01",
  });

  const [evidenceFrame, setEvidenceFrame] = useState(null);

  /* ============================================================
     SYSTEM CHECK
  ============================================================ */

  useEffect(() => {
    checkSystem();

    const interval = setInterval(() => {
      checkSystem();
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  /* ============================================================
     CHECK BACKEND / MOBILE / AI / GPS
  ============================================================ */

  const checkSystem = async () => {
    /* ----------------------------------------------------------
       BACKEND
    ---------------------------------------------------------- */

    try {
      const health = await axios.get(
        `${API_BASE}/api/health`
      );

      setBackendStatus("ONLINE");

      setAiStatus(
        health.data.ai_engine?.toUpperCase() || "READY"
      );
    } catch {
      setBackendStatus("OFFLINE");
      setAiStatus("OFFLINE");
    }

    /* ----------------------------------------------------------
       MOBILE CAMERA
    ---------------------------------------------------------- */

    try {
      const response = await axios.get(
        `${API_BASE}/api/mobile/status`
      );

      setMobileStatus(response.data.status);

      if (response.data.status === "ONLINE") {
        setMobileFrame(
          `${API_BASE}/api/mobile/latest?t=${Date.now()}`
        );
      }
    } catch {
      setMobileStatus("OFFLINE");
    }

    /* ----------------------------------------------------------
       LIVE AI ANALYSIS
    ---------------------------------------------------------- */

    try {
      const aiResponse = await axios.get(
        `${API_BASE}/api/ai/latest?t=${Date.now()}`
      );

      const analysis = aiResponse.data || {};

      setAiAnalysis({
        status: analysis.status || "WAITING",

        camera:
          analysis.camera ||
          "MOBILE-01",

        faces_detected:
          Number(
            analysis.faces_detected ?? 0
          ),

        candidate_target_id:
          analysis.candidate_target_id ||
          null,

        similarity_score:
          Number(
            analysis.similarity_score ?? 0
          ),

        human_review_required:
          Boolean(
            analysis.human_review_required
          ),

        timestamp:
          analysis.timestamp ||
          null,
      });

      /* --------------------------------------------------------
         EVIDENCE
      -------------------------------------------------------- */

      if (
        analysis.status === "POSSIBLE_MATCH"
      ) {
        setEvidenceFrame(
          `${API_BASE}/api/ai/evidence?t=${Date.now()}`
        );
      } else {
        setEvidenceFrame(null);
      }
    } catch {
      setAiAnalysis({
        status: "WAITING",
        camera: "MOBILE-01",
        faces_detected: 0,
        candidate_target_id: null,
        similarity_score: 0,
        human_review_required: false,
        timestamp: null,
      });

      setEvidenceFrame(null);
    }

    /* ----------------------------------------------------------
       GPS LOCATION
    ---------------------------------------------------------- */

    try {
      const locationResponse = await axios.get(
        `${API_BASE}/api/mobile/location?t=${Date.now()}`
      );

      const location =
        locationResponse.data || {};

      setLocationData({
        latitude:
          location.latitude ??
          null,

        longitude:
          location.longitude ??
          null,

        accuracy_m:
          location.accuracy_m ??
          location.accuracy ??
          null,

        updated_at:
          location.updated_at ??
          null,

        camera:
          location.camera ||
          "MOBILE-01",
      });
    } catch {
      /* GPS may not exist yet */
    }
  };

  /* ============================================================
     MOBILE ROUTE
  ============================================================ */

  if (window.location.pathname === "/mobile") {
    return <MobileCamera />;
  }

  /* ============================================================
     AI HELPERS
  ============================================================ */

  const isPossibleMatch =
    aiAnalysis.status === "POSSIBLE_MATCH";

  const isNoMatch =
    aiAnalysis.status === "NO_MATCH";

  const similarityPercentage =
    Number(aiAnalysis.similarity_score || 0) * 100;

  const formattedSimilarity =
    similarityPercentage.toFixed(2);

  /* ============================================================
     MAIN UI
  ============================================================ */

  return (
    <div className="app">

      {/* ======================================================
         HEADER
      ====================================================== */}

      <header className="header">

        <div className="brand">

          <div className="brand-name">
            BORDERSURV
          </div>

          <div className="brand-subtitle">
            AI INTELLIGENT VIDEO ANALYTICS PLATFORM
          </div>

        </div>

        <div className="system-status">

          <span className="status-dot"></span>

          SYSTEM ONLINE

        </div>

      </header>

      {/* ======================================================
         MAIN
      ====================================================== */}

      <main className="main">

        {/* ====================================================
           HERO
        ==================================================== */}

        <section className="hero">

          <div className="hero-content">

            <div className="eyebrow">
              BORDER SECURITY COMMAND CENTER
            </div>

            <h1>
              Intelligent
              <br />
              <span>Surveillance</span>
            </h1>

            <p>
              AI-powered video analytics for intelligent
              monitoring, real-time detection, tracking and
              security event management using existing
              camera infrastructure.
            </p>

            <div className="hero-buttons">

              <button className="primary-button">
                OPEN COMMAND CENTER
              </button>

              <button className="secondary-button">
                CAMERA NETWORK
              </button>

            </div>

          </div>

          {/* SYSTEM CARD */}

          <div className="system-card">

            <div className="card-heading">
              SYSTEM STATUS
            </div>

            <StatusRow
              name="Backend Server"
              status={backendStatus}
            />

            <StatusRow
              name="AI Engine"
              status={aiStatus}
            />

            <StatusRow
              name="Camera Network"
              status="READY"
            />

            <StatusRow
              name="Mobile Camera"
              status={mobileStatus}
            />

          </div>

        </section>

        {/* ====================================================
           MODULES
        ==================================================== */}

        <section className="modules">

          <div className="section-heading">
            SURVEILLANCE MODULES
          </div>

          <div className="module-grid">

            <ModuleCard
              number="01"
              icon="◉"
              title="LIVE CAMERAS"
              description="Monitor connected CCTV, webcam and mobile camera feeds."
            />

            <ModuleCard
              number="02"
              icon="⌁"
              title="AI DETECTION"
              description="Real-time detection of people, vehicles and security events."
            />

            <ModuleCard
              number="03"
              icon="!"
              title="SECURITY ALERTS"
              description="Automatically generate alerts when configured events occur."
            />

            <ModuleCard
              number="04"
              icon="□"
              title="EVIDENCE"
              description="Store detection snapshots, timestamps and event information."
            />

          </div>

        </section>

        {/* ====================================================
           CAMERA NETWORK
        ==================================================== */}

        <section className="camera-section">

          <div className="section-top">

            <div>

              <div className="section-heading">
                CAMERA NETWORK
              </div>

              <div className="section-description">
                Connected surveillance sources
              </div>

            </div>

            <button className="add-camera">
              + ADD CAMERA
            </button>

          </div>

          {/* ==================================================
             CAMERA GRID
          ================================================== */}

          <div className="camera-grid">

            <CameraCard
              camera="CAM-01"
              name="BORDER GATE 01"
              status="ONLINE"
            />

            <CameraCard
              camera="CAM-02"
              name="BORDER ROAD 02"
              status="ONLINE"
            />

            <CameraCard
              camera="CAM-03"
              name="WATCH TOWER 03"
              status="OFFLINE"
            />

            {/* ==================================================
               MOBILE CAMERA + AI ANALYSIS
            ================================================== */}

            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "minmax(0, 1.15fr) minmax(320px, 0.85fr)",
                gap: "18px",
                gridColumn: "1 / -1",
                alignItems: "stretch",
              }}
            >

              {/* =================================================
                 MOBILE CAMERA
              ================================================= */}

              <CameraCard
                camera="MOBILE-01"
                name="MOBILE CAMERA"
                status={mobileStatus}
                image={
                  mobileStatus === "ONLINE"
                    ? mobileFrame
                    : null
                }
              />

              {/* =================================================
                 AI ANALYSIS PANEL
              ================================================= */}

              <div
                style={{
                  border: isPossibleMatch
                    ? "1px solid rgba(255,193,7,0.55)"
                    : "1px solid rgba(0,255,170,0.20)",

                  background: isPossibleMatch
                    ? "linear-gradient(180deg, rgba(255,193,7,0.08), rgba(5,15,24,0.96))"
                    : "linear-gradient(180deg, rgba(0,255,170,0.025), rgba(5,15,24,0.96))",

                  padding: "22px",

                  boxSizing: "border-box",

                  display: "flex",

                  flexDirection: "column",

                  minHeight: "100%",

                  boxShadow: isPossibleMatch
                    ? "0 0 30px rgba(255,193,7,0.08)"
                    : "none",
                }}
              >

                {/* =================================================
                   AI HEADER
                ================================================= */}

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "18px",
                  }}
                >

                  <div
                    style={{
                      fontSize: "11px",
                      letterSpacing: "2px",
                      color: "#9db0c2",
                    }}
                  >
                    AI ANALYSIS
                  </div>

                  <div
                    style={{
                      fontSize: "10px",
                      letterSpacing: "1px",
                      padding: "6px 9px",

                      border:
                        isPossibleMatch
                          ? "1px solid rgba(255,193,7,0.55)"
                          : "1px solid rgba(0,255,170,0.30)",

                      color:
                        isPossibleMatch
                          ? "#ffc107"
                          : "#55d6a5",
                    }}
                  >
                    {isPossibleMatch
                      ? "REVIEW"
                      : "LIVE"}
                  </div>

                </div>

                {/* =================================================
                   STATUS
                ================================================= */}

                <div
                  style={{
                    fontSize: "21px",
                    fontWeight: "700",
                    letterSpacing: "0.5px",
                    marginBottom: "8px",
                  }}
                >

                  {aiAnalysis.status === "POSSIBLE_MATCH"
                    ? "POSSIBLE WATCHLIST MATCH"
                    : aiAnalysis.status === "NO_MATCH"
                      ? "NO MATCH"
                      : "AI ANALYSIS WAITING"}

                </div>

                <div
                  style={{
                    fontSize: "12px",
                    color: "#8297aa",
                    lineHeight: "1.6",
                    marginBottom: "22px",
                  }}
                >

                  {isPossibleMatch
                    ? `Candidate detected on ${aiAnalysis.camera}. Human verification is required.`
                    : isNoMatch
                      ? `No watchlist candidate detected on ${aiAnalysis.camera}.`
                      : "Waiting for live camera analysis."}

                </div>

                {/* =================================================
                   AI STATS
                ================================================= */}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "1fr 1fr",
                    gap: "10px",
                  }}
                >

                  <AIStat
                    label="FACES DETECTED"
                    value={`${aiAnalysis.faces_detected}`}
                  />

                  <AIStat
                    label="SIMILARITY"
                    value={`${formattedSimilarity}%`}
                  />

                  <AIStat
                    label="CAMERA"
                    value={aiAnalysis.camera}
                  />

                  <AIStat
                    label="REVIEW"
                    value={
                      aiAnalysis.human_review_required
                        ? "REQUIRED"
                        : "NOT REQUIRED"
                    }
                  />

                </div>

                {/* =================================================
                   TARGET ID
                ================================================= */}

                {aiAnalysis.candidate_target_id && (
                  <div
                    style={{
                      marginTop: "10px",
                      border:
                        "1px solid rgba(120,150,175,0.18)",
                      background:
                        "rgba(8,20,30,0.7)",
                      padding: "12px",
                    }}
                  >

                    <div
                      style={{
                        fontSize: "9px",
                        letterSpacing: "1.4px",
                        color: "#6f879b",
                        marginBottom: "6px",
                      }}
                    >
                      CANDIDATE TARGET
                    </div>

                    <div
                      style={{
                        fontSize: "11px",
                        fontWeight: "700",
                        wordBreak: "break-all",
                      }}
                    >
                      {aiAnalysis.candidate_target_id}
                    </div>

                  </div>
                )}

                {/* =================================================
                   GPS LOCATION
                ================================================= */}

                <div
                  style={{
                    marginTop: "10px",
                    border:
                      "1px solid rgba(120,150,175,0.18)",
                    background:
                      "rgba(8,20,30,0.7)",
                    padding: "14px",
                  }}
                >

                  <div
                    style={{
                      fontSize: "9px",
                      letterSpacing: "1.5px",
                      color: "#6f879b",
                      marginBottom: "9px",
                    }}
                  >
                    📍 CAMERA LOCATION
                  </div>

                  {locationData.latitude !== null &&
                  locationData.longitude !== null ? (

                    <>
                      <div
                        style={{
                          fontSize: "13px",
                          fontWeight: "700",
                          marginBottom: "5px",
                        }}
                      >
                        {Number(
                          locationData.latitude
                        ).toFixed(6)}
                        {" , "}
                        {Number(
                          locationData.longitude
                        ).toFixed(6)}
                      </div>

                      <div
                        style={{
                          fontSize: "10px",
                          color: "#8297aa",
                        }}
                      >
                        Accuracy:{" "}
                        {locationData.accuracy_m !== null
                          ? `${Number(
                              locationData.accuracy_m
                            ).toFixed(2)} m`
                          : "N/A"}
                      </div>

                      <div
                        style={{
                          fontSize: "10px",
                          color: "#8297aa",
                          marginTop: "4px",
                        }}
                      >
                        Source:{" "}
                        {locationData.camera ||
                          "MOBILE-01"}
                      </div>
                    </>

                  ) : (

                    <div
                      style={{
                        fontSize: "11px",
                        color: "#6f879b",
                      }}
                    >
                      GPS LOCATION WAITING...
                    </div>

                  )}

                </div>

                {/* =================================================
                   TIMESTAMP
                ================================================= */}

                {aiAnalysis.timestamp && (
                  <div
                    style={{
                      fontSize: "9px",
                      color: "#63798b",
                      marginTop: "10px",
                    }}
                  >
                    LAST ANALYSIS:{" "}
                    {new Date(
                      aiAnalysis.timestamp
                    ).toLocaleString()}
                  </div>
                )}

                {/* =================================================
                   EVIDENCE
                ================================================= */}

                {evidenceFrame && (
                  <div
                    style={{
                      marginTop: "18px",
                    }}
                  >

                    <div
                      style={{
                        fontSize: "9px",
                        letterSpacing: "1.5px",
                        color: "#6f879b",
                        marginBottom: "8px",
                      }}
                    >
                      LATEST EVIDENCE
                    </div>

                    <img
                      src={evidenceFrame}
                      alt="Latest AI evidence"
                      style={{
                        width: "100%",
                        height: "180px",
                        objectFit: "cover",
                        display: "block",
                        border:
                          "1px solid rgba(255,193,7,0.25)",
                      }}
                    />

                  </div>
                )}

              </div>

            </div>

          </div>

        </section>

      </main>

      {/* ======================================================
         FOOTER
      ====================================================== */}

      <footer className="footer">

        <div>
          BORDERSURV AI • INTELLIGENT BORDER SURVEILLANCE
        </div>

        <div>
          SYSTEM v1.0
        </div>

      </footer>

    </div>
  );
}

/* ============================================================
   STATUS ROW
============================================================ */

function StatusRow({ name, status }) {
  const offline =
    status === "OFFLINE";

  const waiting =
    status === "WAITING";

  return (
    <div className="status-row">

      <span>
        {name}
      </span>

      <strong
        className={
          offline
            ? "offline"
            : waiting
              ? "waiting"
              : "online"
        }
      >

        <span className="small-dot"></span>

        {status}

      </strong>

    </div>
  );
}

/* ============================================================
   MODULE CARD
============================================================ */

function ModuleCard({
  number,
  icon,
  title,
  description,
}) {
  return (
    <div className="module-card">

      <div className="module-top">

        <span className="module-number">
          {number}
        </span>

        <span className="module-icon">
          {icon}
        </span>

      </div>

      <h3>
        {title}
      </h3>

      <p>
        {description}
      </p>

      <button className="module-button">
        OPEN MODULE →
      </button>

    </div>
  );
}

/* ============================================================
   AI STAT
============================================================ */

function AIStat({
  label,
  value,
}) {
  return (
    <div
      style={{
        border:
          "1px solid rgba(120,150,175,0.18)",

        background:
          "rgba(8,20,30,0.7)",

        padding: "12px",

        minHeight: "62px",

        boxSizing: "border-box",
      }}
    >

      <div
        style={{
          fontSize: "9px",
          letterSpacing: "1.4px",
          color: "#6f879b",
          marginBottom: "6px",
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: "13px",
          fontWeight: "700",
          letterSpacing: "0.4px",
          wordBreak: "break-word",
        }}
      >
        {value}
      </div>

    </div>
  );
}

/* ============================================================
   CAMERA CARD
============================================================ */

function CameraCard({
  camera,
  name,
  status,
  image,
}) {
  const offline =
    status === "OFFLINE";

  const waiting =
    status === "WAITING";

  return (
    <div className="camera-card">

      <div className="camera-screen">

        <div className="camera-label">
          {camera}
        </div>

        {image ? (

          <img
            src={image}
            className="live-camera-image"
            alt={`${name} live feed`}
          />

        ) : (

          <div className="camera-placeholder">

            <div className="camera-symbol">
              ◉
            </div>

            <div>

              {status === "ONLINE"
                ? "LIVE FEED READY"
                : waiting
                  ? "WAITING FOR PHONE"
                  : "NO SIGNAL"}

            </div>

          </div>

        )}

        <div
          className={
            offline
              ? "camera-status offline"
              : waiting
                ? "camera-status waiting"
                : "camera-status online"
          }
        >

          <span className="small-dot"></span>

          {status}

        </div>

      </div>

      <div className="camera-info">

        <div className="camera-name">
          {name}
        </div>

        <div className="camera-meta">

          {camera === "MOBILE-01"
            ? "PHONE CAMERA NODE"
            : "AI ANALYTICS READY"}

        </div>

      </div>

    </div>
  );
}

/* ============================================================
   MOBILE CAMERA PAGE
============================================================ */

function MobileCamera() {

  const videoRef =
    useRef(null);

  const canvasRef =
    useRef(null);

  const [cameraStatus, setCameraStatus] =
    useState("READY");

  const [streaming, setStreaming] =
    useState(false);

  const streamRef =
    useRef(null);

  const sendingRef =
    useRef(false);

  /* ==========================================================
     GPS
  ========================================================== */

  useEffect(() => {

    let watchId = null;

    const sendLocation =
      async (position) => {

        const latitude =
          position.coords.latitude;

        const longitude =
          position.coords.longitude;

        const accuracy =
          position.coords.accuracy;

        console.log(
          "GPS LOCATION RECEIVED"
        );

        console.log(
          "Latitude:",
          latitude
        );

        console.log(
          "Longitude:",
          longitude
        );

        console.log(
          "Accuracy:",
          accuracy
        );

        try {

          const response =
            await axios.post(
              `${API_BASE}/api/mobile/location`,
              {
                latitude,
                longitude,
                accuracy,
              }
            );

          console.log(
            "GPS SENT TO BACKEND:",
            response.data
          );

        } catch (error) {

          console.error(
            "GPS BACKEND ERROR:",
            error
          );

        }
      };

    const gpsError =
      (error) => {

        console.error(
          "GPS ERROR:",
          error.code,
          error.message
        );

      };

    if (!navigator.geolocation) {

      console.error(
        "Geolocation is not supported."
      );

      return;
    }

    /* --------------------------------------------------------
       CURRENT POSITION
    -------------------------------------------------------- */

    navigator.geolocation.getCurrentPosition(
      sendLocation,
      gpsError,
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }
    );

    /* --------------------------------------------------------
       CONTINUOUS GPS
    -------------------------------------------------------- */

    watchId =
      navigator.geolocation.watchPosition(
        sendLocation,
        gpsError,
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 5000,
        }
      );

    return () => {

      if (watchId !== null) {

        navigator.geolocation.clearWatch(
          watchId
        );

      }

    };

  }, []);

  /* ==========================================================
     START CAMERA
  ========================================================== */

  const startCamera =
    async () => {

      try {

        const stream =
          await navigator.mediaDevices.getUserMedia(
            {
              video: {
                facingMode: {
                  ideal: "environment",
                },

                width: {
                  ideal: 1280,
                },

                height: {
                  ideal: 720,
                },
              },

              audio: false,
            }
          );

        streamRef.current =
          stream;

        videoRef.current.srcObject =
          stream;

        await videoRef.current.play();

        setCameraStatus(
          "CAMERA ACTIVE"
        );

        setStreaming(true);

      } catch (error) {

        console.error(error);

        setCameraStatus(
          "CAMERA ACCESS DENIED"
        );

      }
    };

  /* ==========================================================
     STOP CAMERA
  ========================================================== */

  const stopCamera =
    () => {

      if (streamRef.current) {

        streamRef.current
          .getTracks()
          .forEach(
            (track) =>
              track.stop()
          );

      }

      streamRef.current =
        null;

      setStreaming(false);

      setCameraStatus(
        "STOPPED"
      );
    };

  /* ==========================================================
     SEND FRAME LOOP
  ========================================================== */

  useEffect(() => {

    if (!streaming) {
      return;
    }

    const interval =
      setInterval(
        sendFrame,
        500
      );

    return () =>
      clearInterval(interval);

  }, [streaming]);

  /* ==========================================================
     SEND FRAME TO BACKEND
  ========================================================== */

  const sendFrame =
    async () => {

      if (
        sendingRef.current ||
        !videoRef.current ||
        !canvasRef.current
      ) {
        return;
      }

      if (
        videoRef.current.readyState <
        HTMLMediaElement.HAVE_CURRENT_DATA
      ) {
        return;
      }

      sendingRef.current =
        true;

      try {

        const video =
          videoRef.current;

        const canvas =
          canvasRef.current;

        const maxWidth =
          960;

        const scale =
          Math.min(
            1,
            maxWidth /
              video.videoWidth
          );

        canvas.width =
          video.videoWidth *
          scale;

        canvas.height =
          video.videoHeight *
          scale;

        const context =
          canvas.getContext("2d");

        context.drawImage(
          video,
          0,
          0,
          canvas.width,
          canvas.height
        );

        const blob =
          await new Promise(
            (resolve) =>
              canvas.toBlob(
                resolve,
                "image/jpeg",
                0.75
              )
          );

        if (!blob) {
          return;
        }

        const formData =
          new FormData();

        formData.append(
          "file",
          blob,
          "mobile.jpg"
        );

        await fetch(
          `${API_BASE}/api/mobile/frame`,
          {
            method: "POST",
            body: formData,
          }
        );

      } catch (error) {

        console.error(
          "Frame upload error:",
          error
        );

      } finally {

        sendingRef.current =
          false;

      }
    };

  /* ==========================================================
     MOBILE UI
  ========================================================== */

  return (
    <div className="mobile-page">

      <div className="mobile-header">

        <div className="brand-name">
          BORDERSURV
        </div>

        <div className="mobile-node">
          MOBILE SURVEILLANCE NODE
        </div>

      </div>

      <main className="mobile-main">

        <div className="mobile-eyebrow">
          FIELD CAMERA
        </div>

        <h1>
          Mobile Camera
        </h1>

        <p className="mobile-description">
          Use this smartphone as a temporary
          BorderSurv surveillance camera.
        </p>

        <div className="mobile-video-container">

          <video
            ref={videoRef}
            className="mobile-video"
            muted
            playsInline
          />

          {!streaming && (

            <div className="video-overlay">

              <div className="camera-symbol">
                ◉
              </div>

              <div>
                CAMERA READY
              </div>

            </div>

          )}

        </div>

        <canvas
          ref={canvasRef}
          style={{
            display: "none",
          }}
        />

        <div className="mobile-status">

          <span
            className={
              streaming
                ? "status-dot"
                : "status-dot gray"
            }
          ></span>

          {cameraStatus}

        </div>

        <div className="mobile-controls">

          {!streaming ? (

            <button
              className="primary-button mobile-button"
              onClick={startCamera}
            >
              START CAMERA
            </button>

          ) : (

            <button
              className="stop-button"
              onClick={stopCamera}
            >
              STOP CAMERA
            </button>

          )}

        </div>

        <div className="mobile-info">

          <div>
            NODE ID
          </div>

          <strong>
            MOBILE-01
          </strong>

          <div>
            SERVER
          </div>

          <strong>
            {window.location.hostname}
          </strong>

        </div>

      </main>

    </div>
  );
}

/* ============================================================
   EXPORT
============================================================ */

export default App;