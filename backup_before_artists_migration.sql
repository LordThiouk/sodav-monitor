--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: sodav
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO sodav;

--
-- Name: stationstatus; Type: TYPE; Schema: public; Owner: sodav
--

CREATE TYPE public.stationstatus AS ENUM (
    'active',
    'inactive'
);


ALTER TYPE public.stationstatus OWNER TO sodav;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analytics_data; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.analytics_data (
    id integer NOT NULL,
    "timestamp" timestamp without time zone,
    detection_count integer,
    detection_rate double precision,
    active_stations integer,
    average_confidence double precision
);


ALTER TABLE public.analytics_data OWNER TO sodav;

--
-- Name: analytics_data_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.analytics_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.analytics_data_id_seq OWNER TO sodav;

--
-- Name: analytics_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.analytics_data_id_seq OWNED BY public.analytics_data.id;


--
-- Name: artist_daily; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.artist_daily (
    id integer NOT NULL,
    artist_name character varying,
    date timestamp without time zone,
    count integer
);


ALTER TABLE public.artist_daily OWNER TO sodav;

--
-- Name: artist_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.artist_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.artist_daily_id_seq OWNER TO sodav;

--
-- Name: artist_daily_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.artist_daily_id_seq OWNED BY public.artist_daily.id;


--
-- Name: artist_monthly; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.artist_monthly (
    id integer NOT NULL,
    artist_name character varying,
    month timestamp without time zone,
    count integer
);


ALTER TABLE public.artist_monthly OWNER TO sodav;

--
-- Name: artist_monthly_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.artist_monthly_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.artist_monthly_id_seq OWNER TO sodav;

--
-- Name: artist_monthly_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.artist_monthly_id_seq OWNED BY public.artist_monthly.id;


--
-- Name: artist_stats; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.artist_stats (
    id integer NOT NULL,
    artist_name character varying,
    detection_count integer,
    last_detected timestamp without time zone,
    total_play_time interval
);


ALTER TABLE public.artist_stats OWNER TO sodav;

--
-- Name: artist_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.artist_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.artist_stats_id_seq OWNER TO sodav;

--
-- Name: artist_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.artist_stats_id_seq OWNED BY public.artist_stats.id;


--
-- Name: detection_daily; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.detection_daily (
    id integer NOT NULL,
    date timestamp without time zone,
    count integer
);


ALTER TABLE public.detection_daily OWNER TO sodav;

--
-- Name: detection_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.detection_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detection_daily_id_seq OWNER TO sodav;

--
-- Name: detection_daily_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.detection_daily_id_seq OWNED BY public.detection_daily.id;


--
-- Name: detection_hourly; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.detection_hourly (
    id integer NOT NULL,
    hour timestamp without time zone,
    count integer
);


ALTER TABLE public.detection_hourly OWNER TO sodav;

--
-- Name: detection_hourly_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.detection_hourly_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detection_hourly_id_seq OWNER TO sodav;

--
-- Name: detection_hourly_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.detection_hourly_id_seq OWNED BY public.detection_hourly.id;


--
-- Name: detection_monthly; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.detection_monthly (
    id integer NOT NULL,
    month timestamp without time zone,
    count integer
);


ALTER TABLE public.detection_monthly OWNER TO sodav;

--
-- Name: detection_monthly_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.detection_monthly_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detection_monthly_id_seq OWNER TO sodav;

--
-- Name: detection_monthly_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.detection_monthly_id_seq OWNED BY public.detection_monthly.id;


--
-- Name: radio_stations; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.radio_stations (
    id integer NOT NULL,
    name character varying,
    stream_url character varying,
    country character varying,
    language character varying,
    region character varying,
    type character varying,
    status public.stationstatus,
    is_active boolean,
    last_checked timestamp without time zone,
    last_detection_time timestamp without time zone,
    total_play_time interval,
    created_at timestamp without time zone
);


ALTER TABLE public.radio_stations OWNER TO sodav;

--
-- Name: radio_stations_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.radio_stations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.radio_stations_id_seq OWNER TO sodav;

--
-- Name: radio_stations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.radio_stations_id_seq OWNED BY public.radio_stations.id;


--
-- Name: report_subscriptions; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.report_subscriptions (
    id integer NOT NULL,
    name character varying NOT NULL,
    frequency character varying NOT NULL,
    type character varying NOT NULL,
    recipients json NOT NULL,
    next_delivery timestamp without time zone NOT NULL,
    created_at timestamp without time zone,
    last_sent timestamp without time zone,
    is_active boolean,
    user_id integer NOT NULL
);


ALTER TABLE public.report_subscriptions OWNER TO sodav;

--
-- Name: report_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.report_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.report_subscriptions_id_seq OWNER TO sodav;

--
-- Name: report_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.report_subscriptions_id_seq OWNED BY public.report_subscriptions.id;


--
-- Name: reports; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.reports (
    id integer NOT NULL,
    type character varying NOT NULL,
    format character varying NOT NULL,
    status character varying NOT NULL,
    start_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL,
    completed_at timestamp without time zone,
    file_path character varying,
    error_message text,
    filters json,
    user_id integer
);


ALTER TABLE public.reports OWNER TO sodav;

--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reports_id_seq OWNER TO sodav;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.reports_id_seq OWNED BY public.reports.id;


--
-- Name: station_stats; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.station_stats (
    id integer NOT NULL,
    station_id integer,
    detection_count integer,
    last_detected timestamp without time zone,
    average_confidence double precision
);


ALTER TABLE public.station_stats OWNER TO sodav;

--
-- Name: station_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.station_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.station_stats_id_seq OWNER TO sodav;

--
-- Name: station_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.station_stats_id_seq OWNED BY public.station_stats.id;


--
-- Name: station_track_stats; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.station_track_stats (
    id integer NOT NULL,
    station_id integer,
    track_id integer,
    play_count integer,
    total_play_time interval,
    last_played timestamp without time zone,
    average_confidence double precision
);


ALTER TABLE public.station_track_stats OWNER TO sodav;

--
-- Name: station_track_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.station_track_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.station_track_stats_id_seq OWNER TO sodav;

--
-- Name: station_track_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.station_track_stats_id_seq OWNED BY public.station_track_stats.id;


--
-- Name: track_daily; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.track_daily (
    id integer NOT NULL,
    track_id integer,
    date timestamp without time zone,
    count integer
);


ALTER TABLE public.track_daily OWNER TO sodav;

--
-- Name: track_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.track_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.track_daily_id_seq OWNER TO sodav;

--
-- Name: track_daily_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.track_daily_id_seq OWNED BY public.track_daily.id;


--
-- Name: track_detections; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.track_detections (
    id integer NOT NULL,
    station_id integer,
    track_id integer,
    confidence double precision,
    detected_at timestamp without time zone,
    play_duration interval
);


ALTER TABLE public.track_detections OWNER TO sodav;

--
-- Name: track_detections_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.track_detections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.track_detections_id_seq OWNER TO sodav;

--
-- Name: track_detections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.track_detections_id_seq OWNED BY public.track_detections.id;


--
-- Name: track_monthly; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.track_monthly (
    id integer NOT NULL,
    track_id integer,
    month timestamp without time zone,
    count integer
);


ALTER TABLE public.track_monthly OWNER TO sodav;

--
-- Name: track_monthly_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.track_monthly_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.track_monthly_id_seq OWNER TO sodav;

--
-- Name: track_monthly_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.track_monthly_id_seq OWNED BY public.track_monthly.id;


--
-- Name: track_stats; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.track_stats (
    id integer NOT NULL,
    track_id integer,
    detection_count integer,
    average_confidence double precision,
    last_detected timestamp without time zone,
    total_play_time interval
);


ALTER TABLE public.track_stats OWNER TO sodav;

--
-- Name: track_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.track_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.track_stats_id_seq OWNER TO sodav;

--
-- Name: track_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.track_stats_id_seq OWNED BY public.track_stats.id;


--
-- Name: tracks; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.tracks (
    id integer NOT NULL,
    title character varying NOT NULL,
    artist character varying NOT NULL,
    isrc character varying,
    label character varying,
    album character varying,
    release_date timestamp without time zone,
    play_count integer,
    total_play_time interval,
    last_played timestamp without time zone,
    external_ids json,
    created_at timestamp without time zone,
    fingerprint character varying,
    fingerprint_raw bytea
);


ALTER TABLE public.tracks OWNER TO sodav;

--
-- Name: tracks_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.tracks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tracks_id_seq OWNER TO sodav;

--
-- Name: tracks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.tracks_id_seq OWNED BY public.tracks.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: sodav
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying NOT NULL,
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    last_login timestamp without time zone,
    role character varying
);


ALTER TABLE public.users OWNER TO sodav;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: sodav
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO sodav;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sodav
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: analytics_data id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.analytics_data ALTER COLUMN id SET DEFAULT nextval('public.analytics_data_id_seq'::regclass);


--
-- Name: artist_daily id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.artist_daily ALTER COLUMN id SET DEFAULT nextval('public.artist_daily_id_seq'::regclass);


--
-- Name: artist_monthly id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.artist_monthly ALTER COLUMN id SET DEFAULT nextval('public.artist_monthly_id_seq'::regclass);


--
-- Name: artist_stats id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.artist_stats ALTER COLUMN id SET DEFAULT nextval('public.artist_stats_id_seq'::regclass);


--
-- Name: detection_daily id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.detection_daily ALTER COLUMN id SET DEFAULT nextval('public.detection_daily_id_seq'::regclass);


--
-- Name: detection_hourly id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.detection_hourly ALTER COLUMN id SET DEFAULT nextval('public.detection_hourly_id_seq'::regclass);


--
-- Name: detection_monthly id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.detection_monthly ALTER COLUMN id SET DEFAULT nextval('public.detection_monthly_id_seq'::regclass);


--
-- Name: radio_stations id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.radio_stations ALTER COLUMN id SET DEFAULT nextval('public.radio_stations_id_seq'::regclass);


--
-- Name: report_subscriptions id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.report_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.report_subscriptions_id_seq'::regclass);


--
-- Name: reports id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.reports ALTER COLUMN id SET DEFAULT nextval('public.reports_id_seq'::regclass);


--
-- Name: station_stats id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_stats ALTER COLUMN id SET DEFAULT nextval('public.station_stats_id_seq'::regclass);


--
-- Name: station_track_stats id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_track_stats ALTER COLUMN id SET DEFAULT nextval('public.station_track_stats_id_seq'::regclass);


--
-- Name: track_daily id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_daily ALTER COLUMN id SET DEFAULT nextval('public.track_daily_id_seq'::regclass);


--
-- Name: track_detections id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_detections ALTER COLUMN id SET DEFAULT nextval('public.track_detections_id_seq'::regclass);


--
-- Name: track_monthly id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_monthly ALTER COLUMN id SET DEFAULT nextval('public.track_monthly_id_seq'::regclass);


--
-- Name: track_stats id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_stats ALTER COLUMN id SET DEFAULT nextval('public.track_stats_id_seq'::regclass);


--
-- Name: tracks id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.tracks ALTER COLUMN id SET DEFAULT nextval('public.tracks_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: analytics_data; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.analytics_data (id, "timestamp", detection_count, detection_rate, active_stations, average_confidence) FROM stdin;
\.


--
-- Data for Name: artist_daily; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.artist_daily (id, artist_name, date, count) FROM stdin;
\.


--
-- Data for Name: artist_monthly; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.artist_monthly (id, artist_name, month, count) FROM stdin;
\.


--
-- Data for Name: artist_stats; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.artist_stats (id, artist_name, detection_count, last_detected, total_play_time) FROM stdin;
\.


--
-- Data for Name: detection_daily; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.detection_daily (id, date, count) FROM stdin;
\.


--
-- Data for Name: detection_hourly; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.detection_hourly (id, hour, count) FROM stdin;
\.


--
-- Data for Name: detection_monthly; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.detection_monthly (id, month, count) FROM stdin;
\.


--
-- Data for Name: radio_stations; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.radio_stations (id, name, stream_url, country, language, region, type, status, is_active, last_checked, last_detection_time, total_play_time, created_at) FROM stdin;
1	Afia FM 93.0 Dakar	https://stream.zeno.fm/skjrn6kzzxptv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.094492	\N	00:00:00	2025-02-19 17:12:59.134242
2	Bamtaare Dowri FM 92.5 V├®lingara	https://stream.zeno.fm/yy3w3qfpg48uv	Senegal	french,fulani	\N	radio	active	t	2025-02-19 16:12:59.096489	\N	00:00:00	2025-02-19 17:12:59.134242
3	Bamtaare FM 103.4 Dodel	https://stream.zeno.fm/n1mugn1am1duv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.096489	\N	00:00:00	2025-02-19 17:12:59.134242
4	Buu├▒aa FM 91.9 Mampatim	https://stream.zeno.fm/3bfe81fn0c9uv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.097519	\N	00:00:00	2025-02-19 17:12:59.134242
5	Central FM 107.1 Thi├®s	https://stream.zeno.fm/t2e45xqkunhvv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.098489	\N	00:00:00	2025-02-19 17:12:59.134242
6	Dakar Musique	http://listen.senemultimedia.net:8090/stream	Senegal		\N	radio	active	t	2025-02-19 16:12:59.098489	\N	00:00:00	2025-02-19 17:12:59.134242
7	Diassing FM 93.9 Marsassoum	https://stream.zeno.fm/veaguaqvvk8uv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.099519	\N	00:00:00	2025-02-19 17:12:59.134242
8	FM S├®n├®gal 103.1 Dakar	https://stream-154.zeno.fm/t8gcyq6ts0quv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.100519	\N	00:00:00	2025-02-19 17:12:59.134242
9	Gabou FM 106.4 S├®dhiou	https://stream.zeno.fm/xtvgwt362k8uv	Senegal	fulani,mandinka,wolof	\N	radio	active	t	2025-02-19 16:12:59.101512	\N	00:00:00	2025-02-19 17:12:59.134242
10	GMS FM 89.3 Ziguinchor	https://myfm.acan.group/radio/8140/radio.mp3?1690707378	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.101512	\N	00:00:00	2025-02-19 17:12:59.134242
11	H24	http://listen.senemultimedia.net:8070/stream	Senegal		\N	radio	active	t	2025-02-19 16:12:59.102519	\N	00:00:00	2025-02-19 17:12:59.134242
12	H24 Senegal	https://listen.senemultimedia.net:8072/stream	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.103489	\N	00:00:00	2025-02-19 17:12:59.134242
13	Hounar├® FM 95.9 Cas-Cas	https://stream.zeno.fm/h961gztkns8uv	Senegal	french,fulani,hassaniya,soninke,wolof	\N	radio	active	t	2025-02-19 16:12:59.104489	\N	00:00:00	2025-02-19 17:12:59.134242
14	Kaabala FM 97.9 Orkadi├®r├®	https://stream.zeno.fm/uf8pustovp0vv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.104489	\N	00:00:00	2025-02-19 17:12:59.134242
15	Kaolack Online	https://stream.zeno.fm/51taadp6wp9vv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.10552	\N	00:00:00	2025-02-19 17:12:59.134242
16	Love FM 107.3 Dakar	https://stream.zeno.fm/7cru7g7rcwzuv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.106497	\N	00:00:00	2025-02-19 17:12:59.134242
17	Manoor├® FM 89.4 Dakar	https://stream.zeno.fm/sad0xwh0mg8uv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.106497	\N	00:00:00	2025-02-19 17:12:59.134242
18	Mbour FM 96.5	https://stream.zeno.fm/n9z8nz4yvchvv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.107501	\N	00:00:00	2025-02-19 17:12:59.134242
19	Metraf FM 103.7 Dakar	https://stream.zeno.fm/66yrv69ffv8uv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.108501	\N	00:00:00	2025-02-19 17:12:59.134242
20	Or FM 89.6 Orkadi├®r├®	https://stream.zeno.fm/gy7fpc2am1duv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.109545	\N	00:00:00	2025-02-19 17:12:59.134242
21	Pete FM Yeewti Fuuta 102.0	https://stream.zeno.fm/hudhkd8to6xuv	Senegal	fulani,hassaniya,soninke,wolof	\N	radio	active	t	2025-02-19 16:12:59.110499	\N	00:00:00	2025-02-19 17:12:59.134242
22	Pikine Diaspora Radio	http://cdn.voscast.com/resources/?key=563fcd75f43e77334d6fb664b7358f9e&c=winamp	Senegal		\N	radio	active	t	2025-02-19 16:12:59.110499	\N	00:00:00	2025-02-19 17:12:59.134242
23	Radio Al Fayda 90.1 Kaolack	https://usa5.fastcast4u.com/proxy/lyartech?mp=/stream/1/	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.111529	\N	00:00:00	2025-02-19 17:12:59.134242
24	Radio Dakar City	https://listen.senemultimedia.net:8002/stream	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.112504	\N	00:00:00	2025-02-19 17:12:59.134242
25	Radio Fulbe FM 102.6 Dakar	https://stream.zeno.fm/e0grbn8e3rquv	Senegal	fulani	\N	radio	active	t	2025-02-19 16:12:59.113233	\N	00:00:00	2025-02-19 17:12:59.134242
26	Radio Keur Massar	https://stream.keurmassar.info/	Senegal		\N	radio	active	t	2025-02-19 16:12:59.113233	\N	00:00:00	2025-02-19 17:12:59.134242
27	Radio Oxy Jeunes 103.4 Pikine	http://s9.voscast.com:7994/;stream.nsv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.114245	\N	00:00:00	2025-02-19 17:12:59.134242
28	Radio RMI Mojjila Info	https://stream.zeno.fm/5qjahl1jotrvv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.115252	\N	00:00:00	2025-02-19 17:12:59.134242
29	Radio Thiossane	https://listen.senemultimedia.net:8112/stream	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.116242	\N	00:00:00	2025-02-19 17:12:59.134242
30	Rewmi FM 97.5 Dakar	https://stream-61.zeno.fm/nkzsqg16t8quv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.116242	\N	00:00:00	2025-02-19 17:12:59.134242
31	RTS 92.5 RSI	https://10gb1.acangroup.org:8000/rsi	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.117244	\N	00:00:00	2025-02-19 17:12:59.134242
32	RTS Kaolack 103	https://stream.zeno.fm/2fkd4h0ts1duv.m4a	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.118244	\N	00:00:00	2025-02-19 17:12:59.134242
33	RTS Matam 89.1	https://stream.zeno.fm/kxud8vhqt1duv	Senegal	french,fulani	\N	radio	active	t	2025-02-19 16:12:59.119245	\N	00:00:00	2025-02-19 17:12:59.134242
34	RTS Radio Ziguinchor	https://stream.zeno.fm/ua9aunfqt1duv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.120287	\N	00:00:00	2025-02-19 17:12:59.134242
35	RTS Tambacounda 92.0	https://stream.zeno.fm/nqxg7p8pt1duv	Senegal	french,fulani	\N	radio	active	t	2025-02-19 16:12:59.120287	\N	00:00:00	2025-02-19 17:12:59.134242
36	Sud FM Sen Radio	http://stream.zenolive.com/rq40edfn3reuv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.121243	\N	00:00:00	2025-02-19 17:12:59.134242
37	Sweet Radio	https://stream.zeno.fm/jemecjfbczhuv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.122243	\N	00:00:00	2025-02-19 17:12:59.134242
38	Tawfekh FM	https://stream.zeno.fm/aevnaykn64zuv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.123244	\N	00:00:00	2025-02-19 17:12:59.134242
39	Tewdu FM 94.0 Diaoube	https://stream.zeno.fm/wnv7ahdvt98uv	Senegal	french,fulani	\N	radio	active	t	2025-02-19 16:12:59.124247	\N	00:00:00	2025-02-19 17:12:59.134242
40	Timtimol FM 91.9 Ourossogui	https://stream.zeno.fm/4yx608hnu1duv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.126244	\N	00:00:00	2025-02-19 17:12:59.134242
41	Top FM 97.8 Dakar	https://stream.zeno.fm/sys3pbxmhklvv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.126244	\N	00:00:00	2025-02-19 17:12:59.134242
42	UCAD FM 94.7 Dakar	https://stream.zeno.fm/b38a68a1krquv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.127272	\N	00:00:00	2025-02-19 17:12:59.134242
43	V├®lingara FM 95.8	https://stream.zeno.fm/hu2u9pb0mfhvv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.128242	\N	00:00:00	2025-02-19 17:12:59.134242
44	Waar Fi FM 104.9 S├®bikhotane	https://stream.zeno.fm/rmg4rfewweruv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.128242	\N	00:00:00	2025-02-19 17:12:59.134242
45	Walo FM 90.3 Dagana	https://stream.zeno.fm/9ap6q2unephvv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.129243	\N	00:00:00	2025-02-19 17:12:59.134242
46	Zig FM 100.3 Kolda	https://stream.zeno.fm/akh0t25nc18uv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.130272	\N	00:00:00	2025-02-19 17:12:59.134242
47	Zig FM 100.8 Ziguinchor	https://stream.zeno.fm/zfdk0c69d3quv	Senegal	french	\N	radio	active	t	2025-02-19 16:12:59.131241	\N	00:00:00	2025-02-19 17:12:59.134242
\.


--
-- Data for Name: report_subscriptions; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.report_subscriptions (id, name, frequency, type, recipients, next_delivery, created_at, last_sent, is_active, user_id) FROM stdin;
\.


--
-- Data for Name: reports; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.reports (id, type, format, status, start_date, end_date, created_at, completed_at, file_path, error_message, filters, user_id) FROM stdin;
\.


--
-- Data for Name: station_stats; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.station_stats (id, station_id, detection_count, last_detected, average_confidence) FROM stdin;
\.


--
-- Data for Name: station_track_stats; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.station_track_stats (id, station_id, track_id, play_count, total_play_time, last_played, average_confidence) FROM stdin;
\.


--
-- Data for Name: track_daily; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.track_daily (id, track_id, date, count) FROM stdin;
\.


--
-- Data for Name: track_detections; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.track_detections (id, station_id, track_id, confidence, detected_at, play_duration) FROM stdin;
2	6	2	85	2025-02-19 19:11:51.247015	\N
8	24	8	85	2025-02-19 19:20:50.783554	\N
\.


--
-- Data for Name: track_monthly; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.track_monthly (id, track_id, month, count) FROM stdin;
\.


--
-- Data for Name: track_stats; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.track_stats (id, track_id, detection_count, average_confidence, last_detected, total_play_time) FROM stdin;
\.


--
-- Data for Name: tracks; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.tracks (id, title, artist, isrc, label, album, release_date, play_count, total_play_time, last_played, external_ids, created_at, fingerprint, fingerprint_raw) FROM stdin;
1	Boul Ko Fat├®	Amira Abed	FRX452197239	\N	Boul Ko Fat├®	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Boul Ko Fat\\u00e9", "artists": [{"name": "Amira Abed", "id": "4UtWbbJdQl4MXHgZ3Ol6ji", "uri": "spotify:artist:4UtWbbJdQl4MXHgZ3Ol6ji", "href": "https://api.spotify.com/v1/artists/4UtWbbJdQl4MXHgZ3Ol6ji", "external_urls": {"spotify": "https://open.spotify.com/artist/4UtWbbJdQl4MXHgZ3Ol6ji"}}], "album_group": "", "album_type": "single", "id": "4Fktv6mdFAnlxvzS4MvJDW", "uri": "spotify:album:4Fktv6mdFAnlxvzS4MvJDW", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/4Fktv6mdFAnlxvzS4MvJDW", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b273ebfebf5ab6b8a84f2f4f119a"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e02ebfebf5ab6b8a84f2f4f119a"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d00004851ebfebf5ab6b8a84f2f4f119a"}], "external_urls": {"spotify": "https://open.spotify.com/album/4Fktv6mdFAnlxvzS4MvJDW"}, "release_date": "2021-09-10", "release_date_precision": "day"}, "external_ids": {"isrc": "FRX452197239"}, "popularity": 17, "is_playable": true, "linked_from": null, "artists": [{"name": "Amira Abed", "id": "4UtWbbJdQl4MXHgZ3Ol6ji", "uri": "spotify:artist:4UtWbbJdQl4MXHgZ3Ol6ji", "href": "https://api.spotify.com/v1/artists/4UtWbbJdQl4MXHgZ3Ol6ji", "external_urls": {"spotify": "https://open.spotify.com/artist/4UtWbbJdQl4MXHgZ3Ol6ji"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 212727, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/2MKRLiSsNsGkmNvzkLDXtA"}, "href": "https://api.spotify.com/v1/tracks/2MKRLiSsNsGkmNvzkLDXtA", "id": "2MKRLiSsNsGkmNvzkLDXtA", "name": "Boul Ko Fat\\u00e9", "preview_url": "https://p.scdn.co/mp3-preview/d6ef20c89cfda4cffed83209cb9518edfbb59bba?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 1, "uri": "spotify:track:2MKRLiSsNsGkmNvzkLDXtA", "type": "track"}, "deezer": {"id": 1490834752, "readable": true, "title": "Boul Ko Fat\\u00e9", "title_short": "Boul Ko Fat\\u00e9", "title_version": "", "isrc": "FRX452197239", "link": "https://www.deezer.com/track/1490834752", "share": "https://www.deezer.com/track/1490834752?utm_source=deezer&utm_content=track-1490834752&utm_term=1863198382_1739988620&utm_medium=web", "duration": 212, "track_position": 1, "disk_number": 1, "rank": 160964, "release_date": "2021-09-10", "explicit_lyrics": false, "explicit_content_lyrics": 0, "explicit_content_cover": 2, "preview": "https://cdnt-preview.dzcdn.net/api/1/1/8/e/5/0/8e54a972768b5ddb22f49bf4f659465a.mp3?hdnea=exp=1739989520~acl=/api/1/1/8/e/5/0/8e54a972768b5ddb22f49bf4f659465a.mp3*~data=user_id=0,application_id=42~hmac=2aad4606625321b5b3689245b8fb2f158b87fb537c394deeb0dc9658f7ae9e3a", "bpm": 0, "gain": -12, "available_countries": ["AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BN", "BO", "BQ", "BR", "BT", "BV", "BW", "BY", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FR", "GA", "GB", "GD", "GE", "GH", "GM", "GN", "GQ", "GR", "GS", "GT", "GU", "GW", "HK", "HM", "HN", "HR", "HU", "ID", "IE", "IL", "IN", "IO", "IQ", "IR", "IS", "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MD", "ME", "MG", "MH", "MK", "ML", "MM", "MN", "MP", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL", "PN", "PS", "PT", "PW", "PY", "QA", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SI", "SJ", "SK", "SL", "SN", "SO", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VC", "VE", "VG", "VI", "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW"], "contributors": [{"id": 91779692, "name": "Amira Abed", "link": "https://www.deezer.com/artist/91779692", "share": "https://www.deezer.com/artist/91779692?utm_source=deezer&utm_content=artist-91779692&utm_term=1863198382_1739988620&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/91779692/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/91779692/top?limit=50", "type": "artist", "role": "Main"}], "md5_image": "43b450888819ccc2339965ab82ef4fdc", "artist": {"id": 91779692, "name": "Amira Abed", "link": "https://www.deezer.com/artist/91779692", "share": "https://www.deezer.com/artist/91779692?utm_source=deezer&utm_content=artist-91779692&utm_term=1863198382_1739988620&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/91779692/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/c991d219c1f7a7d36ec6cc4ef4cc2bf7/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/91779692/top?limit=50", "type": "artist"}, "album": {"id": 258009262, "title": "Boul Ko Fat\\u00e9", "link": "https://www.deezer.com/album/258009262", "cover": "https://api.deezer.com/2.0/album/258009262/image", "cover_small": "https://cdn-images.dzcdn.net/images/cover/43b450888819ccc2339965ab82ef4fdc/56x56-000000-80-0-0.jpg", "cover_medium": "https://cdn-images.dzcdn.net/images/cover/43b450888819ccc2339965ab82ef4fdc/250x250-000000-80-0-0.jpg", "cover_big": "https://cdn-images.dzcdn.net/images/cover/43b450888819ccc2339965ab82ef4fdc/500x500-000000-80-0-0.jpg", "cover_xl": "https://cdn-images.dzcdn.net/images/cover/43b450888819ccc2339965ab82ef4fdc/1000x1000-000000-80-0-0.jpg", "md5_image": "43b450888819ccc2339965ab82ef4fdc", "release_date": "2021-09-10", "tracklist": "https://api.deezer.com/2.0/album/258009262/tracks", "type": "album"}, "type": "track"}, "musicbrainz": {}}	2025-02-19 19:10:20.746693	\N	\N
2	Carinha de Safada	Eo Mc Dolle Ta	QZHZ62204670	\N	O Melhor no Pique dos Paredoes	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "O Melhor no Pique dos Paredoes", "artists": [{"name": "MC Dolle", "id": "2I04xXqDfjK1YCfAolvK3V", "uri": "spotify:artist:2I04xXqDfjK1YCfAolvK3V", "href": "https://api.spotify.com/v1/artists/2I04xXqDfjK1YCfAolvK3V", "external_urls": {"spotify": "https://open.spotify.com/artist/2I04xXqDfjK1YCfAolvK3V"}}], "album_group": "", "album_type": "single", "id": "5lbYHppDsZTLV9fKc68WIU", "uri": "spotify:album:5lbYHppDsZTLV9fKc68WIU", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/5lbYHppDsZTLV9fKc68WIU", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b27352ad4ccb6daba19575632925"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e0252ad4ccb6daba19575632925"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d0000485152ad4ccb6daba19575632925"}], "external_urls": {"spotify": "https://open.spotify.com/album/5lbYHppDsZTLV9fKc68WIU"}, "release_date": "2022-05-18", "release_date_precision": "day"}, "external_ids": {"isrc": "QZHZ62204670"}, "popularity": 0, "is_playable": true, "linked_from": null, "artists": [{"name": "MC Dolle", "id": "2I04xXqDfjK1YCfAolvK3V", "uri": "spotify:artist:2I04xXqDfjK1YCfAolvK3V", "href": "https://api.spotify.com/v1/artists/2I04xXqDfjK1YCfAolvK3V", "external_urls": {"spotify": "https://open.spotify.com/artist/2I04xXqDfjK1YCfAolvK3V"}}, {"name": "Let\\u00edcia Marjorie", "id": "03oivGAbSNtGUIGxcp7aDq", "uri": "spotify:artist:03oivGAbSNtGUIGxcp7aDq", "href": "https://api.spotify.com/v1/artists/03oivGAbSNtGUIGxcp7aDq", "external_urls": {"spotify": "https://open.spotify.com/artist/03oivGAbSNtGUIGxcp7aDq"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 197566, "explicit": true, "external_urls": {"spotify": "https://open.spotify.com/track/2uo32F1od5BFcg0KsGt5ky"}, "href": "https://api.spotify.com/v1/tracks/2uo32F1od5BFcg0KsGt5ky", "id": "2uo32F1od5BFcg0KsGt5ky", "name": "Carinha de Safada", "preview_url": "https://p.scdn.co/mp3-preview/f40c104b30c0636da6ebaec07d3e3073accb6dc1?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 3, "uri": "spotify:track:2uo32F1od5BFcg0KsGt5ky", "type": "track"}, "deezer": {"id": 1764700987, "readable": true, "title": "Carinha de Safada", "title_short": "Carinha de Safada", "title_version": "", "isrc": "QZHZ62204670", "link": "https://www.deezer.com/track/1764700987", "share": "https://www.deezer.com/track/1764700987?utm_source=deezer&utm_content=track-1764700987&utm_term=1863198382_1739988710&utm_medium=web", "duration": 197, "track_position": 3, "disk_number": 1, "rank": 100000, "release_date": "2022-05-18", "explicit_lyrics": false, "explicit_content_lyrics": 2, "explicit_content_cover": 2, "preview": "https://cdnt-preview.dzcdn.net/api/1/1/5/d/0/0/5d01e3709e04c4136e2b4d35327628d5.mp3?hdnea=exp=1739989610~acl=/api/1/1/5/d/0/0/5d01e3709e04c4136e2b4d35327628d5.mp3*~data=user_id=0,application_id=42~hmac=c0d8671b53d3806d40dd095b39e82c63eda0b2b23be770bd97f0b71db2e98e51", "bpm": 0, "gain": -7.9, "available_countries": ["AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BN", "BO", "BQ", "BR", "BT", "BV", "BW", "BY", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FR", "GA", "GB", "GD", "GE", "GH", "GM", "GN", "GQ", "GR", "GS", "GT", "GU", "GW", "HK", "HM", "HN", "HR", "HU", "ID", "IE", "IL", "IN", "IO", "IQ", "IR", "IS", "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MD", "ME", "MG", "MH", "MK", "ML", "MM", "MN", "MP", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL", "PN", "PS", "PT", "PW", "PY", "QA", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SI", "SJ", "SK", "SL", "SN", "SO", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VC", "VE", "VG", "VI", "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW"], "contributors": [{"id": 171004627, "name": "Eo Mc Dolle Ta", "link": "https://www.deezer.com/artist/171004627", "share": "https://www.deezer.com/artist/171004627?utm_source=deezer&utm_content=artist-171004627&utm_term=1863198382_1739988710&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/171004627/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/171004627/top?limit=50", "type": "artist", "role": "Main"}, {"id": 133565392, "name": "Let\\u00edcia Marjorie", "link": "https://www.deezer.com/artist/133565392", "share": "https://www.deezer.com/artist/133565392?utm_source=deezer&utm_content=artist-133565392&utm_term=1863198382_1739988710&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/133565392/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/4f9513726a45c845384f06792dfa524c/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/4f9513726a45c845384f06792dfa524c/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/4f9513726a45c845384f06792dfa524c/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/4f9513726a45c845384f06792dfa524c/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/133565392/top?limit=50", "type": "artist", "role": "Featured"}], "md5_image": "37862f0fc1efaf981be9cfb0f3556777", "artist": {"id": 171004627, "name": "Eo Mc Dolle Ta", "link": "https://www.deezer.com/artist/171004627", "share": "https://www.deezer.com/artist/171004627?utm_source=deezer&utm_content=artist-171004627&utm_term=1863198382_1739988710&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/171004627/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/37862f0fc1efaf981be9cfb0f3556777/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/171004627/top?limit=50", "type": "artist"}, "album": {"id": 321540807, "title": "O Melhor no Pique dos Paredoes", "link": "https://www.deezer.com/album/321540807", "cover": "https://api.deezer.com/2.0/album/321540807/image", "cover_small": "https://cdn-images.dzcdn.net/images/cover/37862f0fc1efaf981be9cfb0f3556777/56x56-000000-80-0-0.jpg", "cover_medium": "https://cdn-images.dzcdn.net/images/cover/37862f0fc1efaf981be9cfb0f3556777/250x250-000000-80-0-0.jpg", "cover_big": "https://cdn-images.dzcdn.net/images/cover/37862f0fc1efaf981be9cfb0f3556777/500x500-000000-80-0-0.jpg", "cover_xl": "https://cdn-images.dzcdn.net/images/cover/37862f0fc1efaf981be9cfb0f3556777/1000x1000-000000-80-0-0.jpg", "md5_image": "37862f0fc1efaf981be9cfb0f3556777", "release_date": "2022-05-18", "tracklist": "https://api.deezer.com/2.0/album/321540807/tracks", "type": "album"}, "type": "track"}, "musicbrainz": {}}	2025-02-19 19:11:51.224003	\N	\N
3	Africad├½n	Cheikh L├┤	GBBGU9915706	\N	Africad├½n	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Bambay Gueej", "artists": [{"name": "Cheikh L\\u00f4", "id": "6CFWXwqEBUi0UFoIIxmg9h", "uri": "spotify:artist:6CFWXwqEBUi0UFoIIxmg9h", "href": "https://api.spotify.com/v1/artists/6CFWXwqEBUi0UFoIIxmg9h", "external_urls": {"spotify": "https://open.spotify.com/artist/6CFWXwqEBUi0UFoIIxmg9h"}}], "album_group": "", "album_type": "album", "id": "1aNku07x0TFmbnDpqvsOnM", "uri": "spotify:album:1aNku07x0TFmbnDpqvsOnM", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/1aNku07x0TFmbnDpqvsOnM", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b2737badde9571c7859b43659ae9"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e027badde9571c7859b43659ae9"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d000048517badde9571c7859b43659ae9"}], "external_urls": {"spotify": "https://open.spotify.com/album/1aNku07x0TFmbnDpqvsOnM"}, "release_date": "1999-01-01", "release_date_precision": "day"}, "external_ids": {"isrc": "GBBGU9915706"}, "popularity": 10, "is_playable": true, "linked_from": null, "artists": [{"name": "Cheikh L\\u00f4", "id": "6CFWXwqEBUi0UFoIIxmg9h", "uri": "spotify:artist:6CFWXwqEBUi0UFoIIxmg9h", "href": "https://api.spotify.com/v1/artists/6CFWXwqEBUi0UFoIIxmg9h", "external_urls": {"spotify": "https://open.spotify.com/artist/6CFWXwqEBUi0UFoIIxmg9h"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 375080, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/5A5qaH6sOrfEtAJABSRJXJ"}, "href": "https://api.spotify.com/v1/tracks/5A5qaH6sOrfEtAJABSRJXJ", "id": "5A5qaH6sOrfEtAJABSRJXJ", "name": "Africad\\u00ebn", "preview_url": "https://p.scdn.co/mp3-preview/5538c41cbbae13773c4e28feafc9356f3f01d974?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 6, "uri": "spotify:track:5A5qaH6sOrfEtAJABSRJXJ", "type": "track"}, "deezer": {"id": 704075592, "readable": true, "title": "Africad\\u00ebn", "title_short": "Africad\\u00ebn", "title_version": "", "isrc": "GBBGU9915706", "link": "https://www.deezer.com/track/704075592", "share": "https://www.deezer.com/track/704075592?utm_source=deezer&utm_content=track-704075592&utm_term=1863198382_1739988721&utm_medium=web", "duration": 375, "track_position": 6, "disk_number": 1, "rank": 108022, "release_date": "1999-01-01", "explicit_lyrics": false, "explicit_content_lyrics": 0, "explicit_content_cover": 2, "preview": "https://cdnt-preview.dzcdn.net/api/1/1/b/d/5/0/bd51b1a9a98de8227f0d895f9f9ec717.mp3?hdnea=exp=1739989621~acl=/api/1/1/b/d/5/0/bd51b1a9a98de8227f0d895f9f9ec717.mp3*~data=user_id=0,application_id=42~hmac=549336c00f6fac374548354016d9ff36ed92597b01e13b7cfa2effd4e5d9f678", "bpm": 146.1, "gain": -15.9, "available_countries": ["AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BN", "BO", "BQ", "BR", "BT", "BV", "BW", "BY", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CO", "CR", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FR", "GA", "GB", "GD", "GE", "GH", "GM", "GN", "GQ", "GR", "GS", "GT", "GU", "GW", "HK", "HM", "HN", "HR", "HU", "ID", "IE", "IL", "IN", "IO", "IQ", "IS", "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MD", "ME", "MG", "MH", "MK", "ML", "MM", "MN", "MP", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL", "PN", "PS", "PT", "PW", "PY", "QA", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SI", "SJ", "SK", "SL", "SN", "SO", "SS", "ST", "SV", "SX", "SZ", "TC", "TD", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TV", "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VC", "VE", "VG", "VI", "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW"], "contributors": [{"id": 198440, "name": "Cheikh Lo", "link": "https://www.deezer.com/artist/198440", "share": "https://www.deezer.com/artist/198440?utm_source=deezer&utm_content=artist-198440&utm_term=1863198382_1739988721&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/198440/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/198440/top?limit=50", "type": "artist", "role": "Main"}], "md5_image": "fbcd7a889ea4cab2d83b67b0875e725e", "artist": {"id": 198440, "name": "Cheikh Lo", "link": "https://www.deezer.com/artist/198440", "share": "https://www.deezer.com/artist/198440?utm_source=deezer&utm_content=artist-198440&utm_term=1863198382_1739988721&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/198440/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/198440/top?limit=50", "type": "artist"}, "album": {"id": 101848602, "title": "Bambay Gueej", "link": "https://www.deezer.com/album/101848602", "cover": "https://api.deezer.com/2.0/album/101848602/image", "cover_small": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/56x56-000000-80-0-0.jpg", "cover_medium": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/250x250-000000-80-0-0.jpg", "cover_big": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/500x500-000000-80-0-0.jpg", "cover_xl": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/1000x1000-000000-80-0-0.jpg", "md5_image": "fbcd7a889ea4cab2d83b67b0875e725e", "release_date": "2000-03-07", "tracklist": "https://api.deezer.com/2.0/album/101848602/tracks", "type": "album"}, "type": "track"}, "musicbrainz": {"id": "3956dca3-06f4-4790-a114-bcfe108f0679", "score": 100, "title": "Africad\\u00ebn", "length": 375066, "disambiguation": "", "video": null, "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh"}}], "releases": [{"id": "c3668739-b0ad-437a-962e-32ecaec5887d", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "", "country": "XW", "release-events": [{"date": "", "area": {"id": "525d4e18-3d00-31b9-a58b-a146a916de8f", "name": "[Worldwide]", "sort-name": "[Worldwide]", "iso-3166-1-codes": ["XW"]}}], "track-count": 9, "media": [{"position": 1, "format": "Digital Media", "track": [{"id": "cd553ed6-768e-48dd-a461-7552bd2c735d", "number": "6", "title": "Africad\\u00ebn", "length": 375066}], "track-count": 9, "track-offset": 5}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}, {"id": "2a0fda8c-1a0b-402d-8793-93897dbe6963", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "1999-09-27", "country": "GB", "release-events": [{"date": "1999-09-27", "area": {"id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed", "name": "United Kingdom", "sort-name": "United Kingdom", "iso-3166-1-codes": ["GB"]}}], "track-count": 9, "media": [{"position": 1, "format": "CD", "track": [{"id": "a45cb595-897c-3df9-99ae-b5fbb65c1c69", "number": "6", "title": "Africad\\u00ebn", "length": 375080}], "track-count": 9, "track-offset": 5}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}, {"id": "50f2a1e6-bbf5-4ee9-84b2-1144983b3d25", "count": 2, "title": "The Very Best of Africa, Volume 2", "status": "Official", "date": "2004-03-22", "country": "GB", "release-events": [{"date": "2004-03-22", "area": {"id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed", "name": "United Kingdom", "sort-name": "United Kingdom", "iso-3166-1-codes": ["GB"]}}], "track-count": 26, "media": [{"position": 2, "format": "CD", "track": [{"id": "e61e943f-d7ef-31f1-87fc-dc355bf683ab", "number": "5", "title": "Africad\\u00ebn (Senegal)", "length": 373000}], "track-count": 13, "track-offset": 4}], "artist-credit": [{"name": "Various Artists", "artist": {"id": "89ad4ac3-39f7-470e-963a-56509c546377", "name": "Various Artists", "sort-name": "Various Artists", "disambiguation": "add compilations to this artist"}}], "release-group": {"id": "e54e01af-745d-412e-a142-08f44cee78fb", "type-id": "dd2a21e1-0c00-3729-a7a0-de60b84eb5d1", "title": "The Very Best of Africa, Volume 2", "primary-type": "Album", "secondary-types": ["Compilation"]}}, {"id": "f2129a0c-e129-4d53-a694-3daf5dfe337e", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "1999", "country": "US", "release-events": [{"date": "1999", "area": {"id": "489ce91b-6658-3307-9877-795b68554c98", "name": "United States", "sort-name": "United States", "iso-3166-1-codes": ["US"]}}], "track-count": 9, "media": [{"position": 1, "format": "CD", "track": [{"id": "d96aedad-0a39-4663-87a4-905842d89425", "number": "6", "title": "Africad\\u00ebn", "length": 375066}], "track-count": 9, "track-offset": 5}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}], "isrcs": ["GBBGU9915706"], "tags": [{"count": 1, "name": "jazz"}, {"count": 1, "name": "afro-cuban jazz"}, {"count": 2, "name": "afrobeat"}, {"count": 1, "name": "african"}, {"count": 1, "name": "world-fusion"}]}}	2025-02-19 19:12:02.330666	\N	\N
4	Africad├½n	Cheikh L├┤	\N	\N	Africad├½n	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Bambay Gueej", "artists": [{"name": "Cheikh L\\u00f4", "id": "6CFWXwqEBUi0UFoIIxmg9h", "uri": "spotify:artist:6CFWXwqEBUi0UFoIIxmg9h", "href": "https://api.spotify.com/v1/artists/6CFWXwqEBUi0UFoIIxmg9h", "external_urls": {"spotify": "https://open.spotify.com/artist/6CFWXwqEBUi0UFoIIxmg9h"}}], "album_group": "", "album_type": "album", "id": "1aNku07x0TFmbnDpqvsOnM", "uri": "spotify:album:1aNku07x0TFmbnDpqvsOnM", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/1aNku07x0TFmbnDpqvsOnM", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b2737badde9571c7859b43659ae9"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e027badde9571c7859b43659ae9"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d000048517badde9571c7859b43659ae9"}], "external_urls": {"spotify": "https://open.spotify.com/album/1aNku07x0TFmbnDpqvsOnM"}, "release_date": "1999-01-01", "release_date_precision": "day"}, "external_ids": {"isrc": "GBBGU9915706"}, "popularity": 10, "is_playable": true, "linked_from": null, "artists": [{"name": "Cheikh L\\u00f4", "id": "6CFWXwqEBUi0UFoIIxmg9h", "uri": "spotify:artist:6CFWXwqEBUi0UFoIIxmg9h", "href": "https://api.spotify.com/v1/artists/6CFWXwqEBUi0UFoIIxmg9h", "external_urls": {"spotify": "https://open.spotify.com/artist/6CFWXwqEBUi0UFoIIxmg9h"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 375080, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/5A5qaH6sOrfEtAJABSRJXJ"}, "href": "https://api.spotify.com/v1/tracks/5A5qaH6sOrfEtAJABSRJXJ", "id": "5A5qaH6sOrfEtAJABSRJXJ", "name": "Africad\\u00ebn", "preview_url": "https://p.scdn.co/mp3-preview/5538c41cbbae13773c4e28feafc9356f3f01d974?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 6, "uri": "spotify:track:5A5qaH6sOrfEtAJABSRJXJ", "type": "track"}, "deezer": {"id": 704075592, "readable": true, "title": "Africad\\u00ebn", "title_short": "Africad\\u00ebn", "title_version": "", "isrc": "GBBGU9915706", "link": "https://www.deezer.com/track/704075592", "share": "https://www.deezer.com/track/704075592?utm_source=deezer&utm_content=track-704075592&utm_term=1863198382_1739988721&utm_medium=web", "duration": 375, "track_position": 6, "disk_number": 1, "rank": 108022, "release_date": "1999-01-01", "explicit_lyrics": false, "explicit_content_lyrics": 0, "explicit_content_cover": 2, "preview": "https://cdnt-preview.dzcdn.net/api/1/1/b/d/5/0/bd51b1a9a98de8227f0d895f9f9ec717.mp3?hdnea=exp=1739989621~acl=/api/1/1/b/d/5/0/bd51b1a9a98de8227f0d895f9f9ec717.mp3*~data=user_id=0,application_id=42~hmac=549336c00f6fac374548354016d9ff36ed92597b01e13b7cfa2effd4e5d9f678", "bpm": 146.1, "gain": -15.9, "available_countries": ["AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BN", "BO", "BQ", "BR", "BT", "BV", "BW", "BY", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CO", "CR", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FR", "GA", "GB", "GD", "GE", "GH", "GM", "GN", "GQ", "GR", "GS", "GT", "GU", "GW", "HK", "HM", "HN", "HR", "HU", "ID", "IE", "IL", "IN", "IO", "IQ", "IS", "IT", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MD", "ME", "MG", "MH", "MK", "ML", "MM", "MN", "MP", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL", "PN", "PS", "PT", "PW", "PY", "QA", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SI", "SJ", "SK", "SL", "SN", "SO", "SS", "ST", "SV", "SX", "SZ", "TC", "TD", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TV", "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VC", "VE", "VG", "VI", "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW"], "contributors": [{"id": 198440, "name": "Cheikh Lo", "link": "https://www.deezer.com/artist/198440", "share": "https://www.deezer.com/artist/198440?utm_source=deezer&utm_content=artist-198440&utm_term=1863198382_1739988721&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/198440/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/198440/top?limit=50", "type": "artist", "role": "Main"}], "md5_image": "fbcd7a889ea4cab2d83b67b0875e725e", "artist": {"id": 198440, "name": "Cheikh Lo", "link": "https://www.deezer.com/artist/198440", "share": "https://www.deezer.com/artist/198440?utm_source=deezer&utm_content=artist-198440&utm_term=1863198382_1739988721&utm_medium=web", "picture": "https://api.deezer.com/2.0/artist/198440/image", "picture_small": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/56x56-000000-80-0-0.jpg", "picture_medium": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/250x250-000000-80-0-0.jpg", "picture_big": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/500x500-000000-80-0-0.jpg", "picture_xl": "https://cdn-images.dzcdn.net/images/artist/516c03d4862cd327fb344b55feb726cb/1000x1000-000000-80-0-0.jpg", "radio": true, "tracklist": "https://api.deezer.com/2.0/artist/198440/top?limit=50", "type": "artist"}, "album": {"id": 101848602, "title": "Bambay Gueej", "link": "https://www.deezer.com/album/101848602", "cover": "https://api.deezer.com/2.0/album/101848602/image", "cover_small": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/56x56-000000-80-0-0.jpg", "cover_medium": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/250x250-000000-80-0-0.jpg", "cover_big": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/500x500-000000-80-0-0.jpg", "cover_xl": "https://cdn-images.dzcdn.net/images/cover/fbcd7a889ea4cab2d83b67b0875e725e/1000x1000-000000-80-0-0.jpg", "md5_image": "fbcd7a889ea4cab2d83b67b0875e725e", "release_date": "2000-03-07", "tracklist": "https://api.deezer.com/2.0/album/101848602/tracks", "type": "album"}, "type": "track"}, "musicbrainz": {"id": "3956dca3-06f4-4790-a114-bcfe108f0679", "score": 100, "title": "Africad\\u00ebn", "length": 375066, "disambiguation": "", "video": null, "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh"}}], "releases": [{"id": "c3668739-b0ad-437a-962e-32ecaec5887d", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "", "country": "XW", "release-events": [{"date": "", "area": {"id": "525d4e18-3d00-31b9-a58b-a146a916de8f", "name": "[Worldwide]", "sort-name": "[Worldwide]", "iso-3166-1-codes": ["XW"]}}], "track-count": 9, "media": [{"position": 1, "format": "Digital Media", "track": [{"id": "cd553ed6-768e-48dd-a461-7552bd2c735d", "number": "6", "title": "Africad\\u00ebn", "length": 375066}], "track-count": 9, "track-offset": 5}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}, {"id": "2a0fda8c-1a0b-402d-8793-93897dbe6963", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "1999-09-27", "country": "GB", "release-events": [{"date": "1999-09-27", "area": {"id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed", "name": "United Kingdom", "sort-name": "United Kingdom", "iso-3166-1-codes": ["GB"]}}], "track-count": 9, "media": [{"position": 1, "format": "CD", "track": [{"id": "a45cb595-897c-3df9-99ae-b5fbb65c1c69", "number": "6", "title": "Africad\\u00ebn", "length": 375080}], "track-count": 9, "track-offset": 5}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}, {"id": "50f2a1e6-bbf5-4ee9-84b2-1144983b3d25", "count": 2, "title": "The Very Best of Africa, Volume 2", "status": "Official", "date": "2004-03-22", "country": "GB", "release-events": [{"date": "2004-03-22", "area": {"id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed", "name": "United Kingdom", "sort-name": "United Kingdom", "iso-3166-1-codes": ["GB"]}}], "track-count": 26, "media": [{"position": 2, "format": "CD", "track": [{"id": "e61e943f-d7ef-31f1-87fc-dc355bf683ab", "number": "5", "title": "Africad\\u00ebn (Senegal)", "length": 373000}], "track-count": 13, "track-offset": 4}], "artist-credit": [{"name": "Various Artists", "artist": {"id": "89ad4ac3-39f7-470e-963a-56509c546377", "name": "Various Artists", "sort-name": "Various Artists", "disambiguation": "add compilations to this artist"}}], "release-group": {"id": "e54e01af-745d-412e-a142-08f44cee78fb", "type-id": "dd2a21e1-0c00-3729-a7a0-de60b84eb5d1", "title": "The Very Best of Africa, Volume 2", "primary-type": "Album", "secondary-types": ["Compilation"]}}, {"id": "f2129a0c-e129-4d53-a694-3daf5dfe337e", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "1999", "country": "US", "release-events": [{"date": "1999", "area": {"id": "489ce91b-6658-3307-9877-795b68554c98", "name": "United States", "sort-name": "United States", "iso-3166-1-codes": ["US"]}}], "track-count": 9, "media": [{"position": 1, "format": "CD", "track": [{"id": "d96aedad-0a39-4663-87a4-905842d89425", "number": "6", "title": "Africad\\u00ebn", "length": 375066}], "track-count": 9, "track-offset": 5}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}], "isrcs": ["GBBGU9915706"], "tags": [{"count": 1, "name": "jazz"}, {"count": 1, "name": "afro-cuban jazz"}, {"count": 2, "name": "afrobeat"}, {"count": 1, "name": "african"}, {"count": 1, "name": "world-fusion"}]}}	2025-02-19 19:13:16.125739	\N	\N
5	Madrid City	Ana Mena	ES5022302278	\N	Madrid City	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Madrid City", "artists": [{"name": "Ana Mena", "id": "6k8mwkKJKKjBILo7ypBspl", "uri": "spotify:artist:6k8mwkKJKKjBILo7ypBspl", "href": "https://api.spotify.com/v1/artists/6k8mwkKJKKjBILo7ypBspl", "external_urls": {"spotify": "https://open.spotify.com/artist/6k8mwkKJKKjBILo7ypBspl"}}], "album_group": "", "album_type": "single", "id": "10FIZ9MLyrK0ddmsMmDE98", "uri": "spotify:album:10FIZ9MLyrK0ddmsMmDE98", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/10FIZ9MLyrK0ddmsMmDE98", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b2739c3dc8b4e881fd2607687a8b"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e029c3dc8b4e881fd2607687a8b"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d000048519c3dc8b4e881fd2607687a8b"}], "external_urls": {"spotify": "https://open.spotify.com/album/10FIZ9MLyrK0ddmsMmDE98"}, "release_date": "2023-09-29", "release_date_precision": "day"}, "external_ids": {"isrc": "ES5022302278"}, "popularity": 62, "is_playable": true, "linked_from": null, "artists": [{"name": "Ana Mena", "id": "6k8mwkKJKKjBILo7ypBspl", "uri": "spotify:artist:6k8mwkKJKKjBILo7ypBspl", "href": "https://api.spotify.com/v1/artists/6k8mwkKJKKjBILo7ypBspl", "external_urls": {"spotify": "https://open.spotify.com/artist/6k8mwkKJKKjBILo7ypBspl"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 172727, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/6KHxe3Yj8W8oq3zviUvJRe"}, "href": "https://api.spotify.com/v1/tracks/6KHxe3Yj8W8oq3zviUvJRe", "id": "6KHxe3Yj8W8oq3zviUvJRe", "name": "Madrid City", "preview_url": "https://p.scdn.co/mp3-preview/31d97925e7321d8a408f31aaf1db9dad4f387a6f?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 1, "uri": "spotify:track:6KHxe3Yj8W8oq3zviUvJRe", "type": "track"}, "deezer": {}, "musicbrainz": {"id": "ad96321c-dd66-47ef-9bd3-0ac1f88ff98b", "score": 100, "title": "Madrid City", "length": 174000, "disambiguation": "", "video": null, "artist-credit": [{"name": "Ana Mena", "artist": {"id": "905d9c0c-0632-4fab-a7b5-7d33b9699907", "name": "Ana Mena", "sort-name": "Mena, Ana"}}], "releases": [{"id": "c430f21c-5cce-456a-a2a4-19d64aa5348f", "count": 3, "title": "NRJ Summer Hits Only 2024", "status": "", "date": "2024-06-21", "country": "FR", "release-events": [{"date": "2024-06-21", "area": {"id": "08310658-51eb-3801-80de-5a0739207115", "name": "France", "sort-name": "France", "iso-3166-1-codes": ["FR"]}}], "track-count": 51, "media": [{"position": 2, "format": "CD", "track": [{"id": "384fabed-0d04-4131-b2c2-5ad1a9021d34", "number": "17", "title": "Madrid City", "length": 174000}], "track-count": 17, "track-offset": 16}], "artist-credit": [{"name": "Various Artists", "artist": {"id": "89ad4ac3-39f7-470e-963a-56509c546377", "name": "Various Artists", "sort-name": "Various Artists", "disambiguation": "add compilations to this artist"}}], "release-group": {"id": "ad092cd3-3870-434f-9104-410ff9a16398", "type-id": "dd2a21e1-0c00-3729-a7a0-de60b84eb5d1", "title": "NRJ Summer Hits Only 2024", "primary-type": "Album", "secondary-types": ["Compilation"]}}, {"id": "4bbab476-c7d2-4056-8bb0-4525f0ab342a", "count": 3, "title": "NRJ Hit Music Only! 2024", "status": "Official", "date": "2024-04-05", "country": "FR", "release-events": [{"date": "2024-04-05", "area": {"id": "08310658-51eb-3801-80de-5a0739207115", "name": "France", "sort-name": "France", "iso-3166-1-codes": ["FR"]}}], "track-count": 48, "media": [{"position": 1, "format": "CD", "track": [{"id": "d744200c-3ace-4022-8315-06ef387e52a1", "number": "7", "title": "Madrid City", "length": 174000}], "track-count": 16, "track-offset": 6}], "artist-credit": [{"name": "Various Artists", "artist": {"id": "89ad4ac3-39f7-470e-963a-56509c546377", "name": "Various Artists", "sort-name": "Various Artists", "disambiguation": "add compilations to this artist"}}], "release-group": {"id": "1945fd3e-b432-4d70-b340-910a249d741d", "type-id": "dd2a21e1-0c00-3729-a7a0-de60b84eb5d1", "title": "NRJ Hit Music Only! 2024", "primary-type": "Album", "secondary-types": ["Compilation"]}}, {"id": "06d7750a-23d0-4f41-a31d-867b31fa762b", "count": 1, "title": "Madrid City", "status": "Official", "date": "2023-09-29", "country": "XW", "release-events": [{"date": "2023-09-29", "area": {"id": "525d4e18-3d00-31b9-a58b-a146a916de8f", "name": "[Worldwide]", "sort-name": "[Worldwide]", "iso-3166-1-codes": ["XW"]}}], "track-count": 1, "media": [{"position": 1, "format": "Digital Media", "track": [{"id": "e8053370-4758-47c8-9784-b9aeb5925a02", "number": "1", "title": "Madrid City", "length": 172727}], "track-count": 1, "track-offset": 0}], "artist-credit": [{"name": "Ana Mena", "artist": {"id": "905d9c0c-0632-4fab-a7b5-7d33b9699907", "name": "Ana Mena", "sort-name": "Mena, Ana", "disambiguation": "Spanish singer and actress"}}], "release-group": {"id": "09186def-3593-4b4c-8eee-53476cb1821b", "type-id": "d6038452-8ee0-3f68-affc-2de9a1ede0b9", "title": "Madrid City", "primary-type": "Single", "secondary-types": null}}], "isrcs": ["ES5022302278"], "tags": null}}	2025-02-19 19:17:45.931061	\N	\N
6	N'Dawsile	Cheikh L├┤	GBBGU9915705	\N	N'Dawsile	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Bambay Gueej", "artists": [{"name": "Cheikh L\\u00f4", "id": "6CFWXwqEBUi0UFoIIxmg9h", "uri": "spotify:artist:6CFWXwqEBUi0UFoIIxmg9h", "href": "https://api.spotify.com/v1/artists/6CFWXwqEBUi0UFoIIxmg9h", "external_urls": {"spotify": "https://open.spotify.com/artist/6CFWXwqEBUi0UFoIIxmg9h"}}], "album_group": "", "album_type": "album", "id": "1aNku07x0TFmbnDpqvsOnM", "uri": "spotify:album:1aNku07x0TFmbnDpqvsOnM", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/1aNku07x0TFmbnDpqvsOnM", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b2737badde9571c7859b43659ae9"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e027badde9571c7859b43659ae9"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d000048517badde9571c7859b43659ae9"}], "external_urls": {"spotify": "https://open.spotify.com/album/1aNku07x0TFmbnDpqvsOnM"}, "release_date": "1999-01-01", "release_date_precision": "day"}, "external_ids": {"isrc": "GBBGU9915705"}, "popularity": 8, "is_playable": true, "linked_from": null, "artists": [{"name": "Cheikh L\\u00f4", "id": "6CFWXwqEBUi0UFoIIxmg9h", "uri": "spotify:artist:6CFWXwqEBUi0UFoIIxmg9h", "href": "https://api.spotify.com/v1/artists/6CFWXwqEBUi0UFoIIxmg9h", "external_urls": {"spotify": "https://open.spotify.com/artist/6CFWXwqEBUi0UFoIIxmg9h"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 377093, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/0P91z449W0aRysCphUwJoz"}, "href": "https://api.spotify.com/v1/tracks/0P91z449W0aRysCphUwJoz", "id": "0P91z449W0aRysCphUwJoz", "name": "N'dawsile", "preview_url": "https://p.scdn.co/mp3-preview/6415202f1d9a9f8554fcbded7c5daa0f5c868b9d?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 5, "uri": "spotify:track:0P91z449W0aRysCphUwJoz", "type": "track"}, "deezer": {}, "musicbrainz": {"id": "698358cb-f0f4-4c25-b1f0-39d53f16e7f3", "score": 100, "title": "N\\u2019Dawsile", "length": 377093, "disambiguation": "", "video": null, "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh"}}], "releases": [{"id": "c3668739-b0ad-437a-962e-32ecaec5887d", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "", "country": "XW", "release-events": [{"date": "", "area": {"id": "525d4e18-3d00-31b9-a58b-a146a916de8f", "name": "[Worldwide]", "sort-name": "[Worldwide]", "iso-3166-1-codes": ["XW"]}}], "track-count": 9, "media": [{"position": 1, "format": "Digital Media", "track": [{"id": "657a6b04-248b-4195-b953-648efb698455", "number": "5", "title": "N\\u2019Dawsile", "length": 377093}], "track-count": 9, "track-offset": 4}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}, {"id": "2a0fda8c-1a0b-402d-8793-93897dbe6963", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "1999-09-27", "country": "GB", "release-events": [{"date": "1999-09-27", "area": {"id": "8a754a16-0027-3a29-b6d7-2b40ea0481ed", "name": "United Kingdom", "sort-name": "United Kingdom", "iso-3166-1-codes": ["GB"]}}], "track-count": 9, "media": [{"position": 1, "format": "CD", "track": [{"id": "d2935bb4-9037-3c5e-96ce-d65cd124ab80", "number": "5", "title": "N'Dawsile", "length": 377093}], "track-count": 9, "track-offset": 4}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}, {"id": "f2129a0c-e129-4d53-a694-3daf5dfe337e", "count": 1, "title": "Bambay Gueej", "status": "Official", "date": "1999", "country": "US", "release-events": [{"date": "1999", "area": {"id": "489ce91b-6658-3307-9877-795b68554c98", "name": "United States", "sort-name": "United States", "iso-3166-1-codes": ["US"]}}], "track-count": 9, "media": [{"position": 1, "format": "CD", "track": [{"id": "e4b4d22b-9943-45fa-bfb8-86621272d3d5", "number": "5", "title": "N'Dawsile", "length": 377093}], "track-count": 9, "track-offset": 4}], "artist-credit": [{"name": "Cheikh L\\u00f4", "artist": {"id": "0b1e097a-4afa-4e82-b5ef-b49cfcb54927", "name": "Cheikh L\\u00f4", "sort-name": "L\\u00f4, Cheikh", "disambiguation": ""}}], "release-group": {"id": "3266fbaf-2b18-3701-9852-39ff36a2f33d", "type-id": "f529b476-6e62-324f-b0aa-1f3e33d313fc", "title": "Bambay Gueej", "primary-type": "Album", "secondary-types": null}}], "isrcs": ["GBBGU9915705"], "tags": [{"count": 1, "name": "jazz"}, {"count": 1, "name": "afro-cuban jazz"}, {"count": 1, "name": "afrobeat"}, {"count": 1, "name": "african"}, {"count": 1, "name": "world-fusion"}]}}	2025-02-19 19:18:05.360713	\N	\N
7	Madrid City	Ana Mena	\N	\N	Madrid City	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Madrid City", "artists": [{"name": "Ana Mena", "id": "6k8mwkKJKKjBILo7ypBspl", "uri": "spotify:artist:6k8mwkKJKKjBILo7ypBspl", "href": "https://api.spotify.com/v1/artists/6k8mwkKJKKjBILo7ypBspl", "external_urls": {"spotify": "https://open.spotify.com/artist/6k8mwkKJKKjBILo7ypBspl"}}], "album_group": "", "album_type": "single", "id": "10FIZ9MLyrK0ddmsMmDE98", "uri": "spotify:album:10FIZ9MLyrK0ddmsMmDE98", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/10FIZ9MLyrK0ddmsMmDE98", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b2739c3dc8b4e881fd2607687a8b"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e029c3dc8b4e881fd2607687a8b"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d000048519c3dc8b4e881fd2607687a8b"}], "external_urls": {"spotify": "https://open.spotify.com/album/10FIZ9MLyrK0ddmsMmDE98"}, "release_date": "2023-09-29", "release_date_precision": "day"}, "external_ids": {"isrc": "ES5022302278"}, "popularity": 62, "is_playable": true, "linked_from": null, "artists": [{"name": "Ana Mena", "id": "6k8mwkKJKKjBILo7ypBspl", "uri": "spotify:artist:6k8mwkKJKKjBILo7ypBspl", "href": "https://api.spotify.com/v1/artists/6k8mwkKJKKjBILo7ypBspl", "external_urls": {"spotify": "https://open.spotify.com/artist/6k8mwkKJKKjBILo7ypBspl"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 172727, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/6KHxe3Yj8W8oq3zviUvJRe"}, "href": "https://api.spotify.com/v1/tracks/6KHxe3Yj8W8oq3zviUvJRe", "id": "6KHxe3Yj8W8oq3zviUvJRe", "name": "Madrid City", "preview_url": "https://p.scdn.co/mp3-preview/31d97925e7321d8a408f31aaf1db9dad4f387a6f?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 1, "uri": "spotify:track:6KHxe3Yj8W8oq3zviUvJRe", "type": "track"}, "deezer": {}, "musicbrainz": {"id": "ad96321c-dd66-47ef-9bd3-0ac1f88ff98b", "score": 100, "title": "Madrid City", "length": 174000, "disambiguation": "", "video": null, "artist-credit": [{"name": "Ana Mena", "artist": {"id": "905d9c0c-0632-4fab-a7b5-7d33b9699907", "name": "Ana Mena", "sort-name": "Mena, Ana"}}], "releases": [{"id": "c430f21c-5cce-456a-a2a4-19d64aa5348f", "count": 3, "title": "NRJ Summer Hits Only 2024", "status": "", "date": "2024-06-21", "country": "FR", "release-events": [{"date": "2024-06-21", "area": {"id": "08310658-51eb-3801-80de-5a0739207115", "name": "France", "sort-name": "France", "iso-3166-1-codes": ["FR"]}}], "track-count": 51, "media": [{"position": 2, "format": "CD", "track": [{"id": "384fabed-0d04-4131-b2c2-5ad1a9021d34", "number": "17", "title": "Madrid City", "length": 174000}], "track-count": 17, "track-offset": 16}], "artist-credit": [{"name": "Various Artists", "artist": {"id": "89ad4ac3-39f7-470e-963a-56509c546377", "name": "Various Artists", "sort-name": "Various Artists", "disambiguation": "add compilations to this artist"}}], "release-group": {"id": "ad092cd3-3870-434f-9104-410ff9a16398", "type-id": "dd2a21e1-0c00-3729-a7a0-de60b84eb5d1", "title": "NRJ Summer Hits Only 2024", "primary-type": "Album", "secondary-types": ["Compilation"]}}, {"id": "4bbab476-c7d2-4056-8bb0-4525f0ab342a", "count": 3, "title": "NRJ Hit Music Only! 2024", "status": "Official", "date": "2024-04-05", "country": "FR", "release-events": [{"date": "2024-04-05", "area": {"id": "08310658-51eb-3801-80de-5a0739207115", "name": "France", "sort-name": "France", "iso-3166-1-codes": ["FR"]}}], "track-count": 48, "media": [{"position": 1, "format": "CD", "track": [{"id": "d744200c-3ace-4022-8315-06ef387e52a1", "number": "7", "title": "Madrid City", "length": 174000}], "track-count": 16, "track-offset": 6}], "artist-credit": [{"name": "Various Artists", "artist": {"id": "89ad4ac3-39f7-470e-963a-56509c546377", "name": "Various Artists", "sort-name": "Various Artists", "disambiguation": "add compilations to this artist"}}], "release-group": {"id": "1945fd3e-b432-4d70-b340-910a249d741d", "type-id": "dd2a21e1-0c00-3729-a7a0-de60b84eb5d1", "title": "NRJ Hit Music Only! 2024", "primary-type": "Album", "secondary-types": ["Compilation"]}}, {"id": "06d7750a-23d0-4f41-a31d-867b31fa762b", "count": 1, "title": "Madrid City", "status": "Official", "date": "2023-09-29", "country": "XW", "release-events": [{"date": "2023-09-29", "area": {"id": "525d4e18-3d00-31b9-a58b-a146a916de8f", "name": "[Worldwide]", "sort-name": "[Worldwide]", "iso-3166-1-codes": ["XW"]}}], "track-count": 1, "media": [{"position": 1, "format": "Digital Media", "track": [{"id": "e8053370-4758-47c8-9784-b9aeb5925a02", "number": "1", "title": "Madrid City", "length": 172727}], "track-count": 1, "track-offset": 0}], "artist-credit": [{"name": "Ana Mena", "artist": {"id": "905d9c0c-0632-4fab-a7b5-7d33b9699907", "name": "Ana Mena", "sort-name": "Mena, Ana", "disambiguation": "Spanish singer and actress"}}], "release-group": {"id": "09186def-3593-4b4c-8eee-53476cb1821b", "type-id": "d6038452-8ee0-3f68-affc-2de9a1ede0b9", "title": "Madrid City", "primary-type": "Single", "secondary-types": null}}], "isrcs": ["ES5022302278"], "tags": null}}	2025-02-19 19:19:13.318421	\N	\N
8	Show Me Who You Are	Mark Nevin	UKW3Z2102428	\N	Show Me Who You Are	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "Show Me Who You Are", "artists": [{"name": "Mark Nevin", "id": "3dHlJGaasnxa9FWa55b0nR", "uri": "spotify:artist:3dHlJGaasnxa9FWa55b0nR", "href": "https://api.spotify.com/v1/artists/3dHlJGaasnxa9FWa55b0nR", "external_urls": {"spotify": "https://open.spotify.com/artist/3dHlJGaasnxa9FWa55b0nR"}}], "album_group": "", "album_type": "single", "id": "0VZCjwM9AnLfOYno9ktfBN", "uri": "spotify:album:0VZCjwM9AnLfOYno9ktfBN", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/0VZCjwM9AnLfOYno9ktfBN", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b273fcb878bb5f9d7ff8b411378e"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e02fcb878bb5f9d7ff8b411378e"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d00004851fcb878bb5f9d7ff8b411378e"}], "external_urls": {"spotify": "https://open.spotify.com/album/0VZCjwM9AnLfOYno9ktfBN"}, "release_date": "2022-01-21", "release_date_precision": "day"}, "external_ids": {"isrc": "UKW3Z2102428"}, "popularity": 17, "is_playable": true, "linked_from": null, "artists": [{"name": "Mark Nevin", "id": "3dHlJGaasnxa9FWa55b0nR", "uri": "spotify:artist:3dHlJGaasnxa9FWa55b0nR", "href": "https://api.spotify.com/v1/artists/3dHlJGaasnxa9FWa55b0nR", "external_urls": {"spotify": "https://open.spotify.com/artist/3dHlJGaasnxa9FWa55b0nR"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 274560, "explicit": false, "external_urls": {"spotify": "https://open.spotify.com/track/3yUu7Mx4CHMFm3NASQw76l"}, "href": "https://api.spotify.com/v1/tracks/3yUu7Mx4CHMFm3NASQw76l", "id": "3yUu7Mx4CHMFm3NASQw76l", "name": "Show Me Who You Are", "preview_url": "https://p.scdn.co/mp3-preview/c1c025ed755e63a66fac4f484a82a88b77af42aa?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 1, "uri": "spotify:track:3yUu7Mx4CHMFm3NASQw76l", "type": "track"}, "deezer": {}, "musicbrainz": {}}	2025-02-19 19:20:50.765526	\N	\N
9	The Look in Your Eyes	JR	US3L61575981	\N	The Look in Your Eyes	\N	0	00:00:00	\N	{"spotify": {"album": {"name": "The Look in Your Eyes", "artists": [{"name": "JR", "id": "7Ikq8LKTY23eLtjYSgroC9", "uri": "spotify:artist:7Ikq8LKTY23eLtjYSgroC9", "href": "https://api.spotify.com/v1/artists/7Ikq8LKTY23eLtjYSgroC9", "external_urls": {"spotify": "https://open.spotify.com/artist/7Ikq8LKTY23eLtjYSgroC9"}}], "album_group": "", "album_type": "single", "id": "4AmpBQs6draA4UGgwxfSoE", "uri": "spotify:album:4AmpBQs6draA4UGgwxfSoE", "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "href": "https://api.spotify.com/v1/albums/4AmpBQs6draA4UGgwxfSoE", "images": [{"height": 640, "width": 640, "url": "https://i.scdn.co/image/ab67616d0000b273dd4ae27ce2a3c403d39cba8f"}, {"height": 300, "width": 300, "url": "https://i.scdn.co/image/ab67616d00001e02dd4ae27ce2a3c403d39cba8f"}, {"height": 64, "width": 64, "url": "https://i.scdn.co/image/ab67616d00004851dd4ae27ce2a3c403d39cba8f"}], "external_urls": {"spotify": "https://open.spotify.com/album/4AmpBQs6draA4UGgwxfSoE"}, "release_date": "2016-03-24", "release_date_precision": "day"}, "external_ids": {"isrc": "US3L61575981"}, "popularity": 0, "is_playable": true, "linked_from": null, "artists": [{"name": "JR", "id": "7Ikq8LKTY23eLtjYSgroC9", "uri": "spotify:artist:7Ikq8LKTY23eLtjYSgroC9", "href": "https://api.spotify.com/v1/artists/7Ikq8LKTY23eLtjYSgroC9", "external_urls": {"spotify": "https://open.spotify.com/artist/7Ikq8LKTY23eLtjYSgroC9"}}], "available_markets": ["AR", "AU", "AT", "BE", "BO", "BR", "BG", "CA", "CL", "CO", "CR", "CY", "CZ", "DK", "DO", "DE", "EC", "EE", "SV", "FI", "FR", "GR", "GT", "HN", "HK", "HU", "IS", "IE", "IT", "LV", "LT", "LU", "MY", "MT", "MX", "NL", "NZ", "NI", "NO", "PA", "PY", "PE", "PH", "PL", "PT", "SG", "SK", "ES", "SE", "CH", "TW", "TR", "UY", "US", "GB", "AD", "LI", "MC", "ID", "JP", "TH", "VN", "RO", "IL", "ZA", "SA", "AE", "BH", "QA", "OM", "KW", "EG", "MA", "DZ", "TN", "LB", "JO", "PS", "IN", "BY", "KZ", "MD", "UA", "AL", "BA", "HR", "ME", "MK", "RS", "SI", "KR", "BD", "PK", "LK", "GH", "KE", "NG", "TZ", "UG", "AG", "AM", "BS", "BB", "BZ", "BT", "BW", "BF", "CV", "CW", "DM", "FJ", "GM", "GE", "GD", "GW", "GY", "HT", "JM", "KI", "LS", "LR", "MW", "MV", "ML", "MH", "FM", "NA", "NR", "NE", "PW", "PG", "PR", "WS", "SM", "ST", "SN", "SC", "SL", "SB", "KN", "LC", "VC", "SR", "TL", "TO", "TT", "TV", "VU", "AZ", "BN", "BI", "KH", "CM", "TD", "KM", "GQ", "SZ", "GA", "GN", "KG", "LA", "MO", "MR", "MN", "NP", "RW", "TG", "UZ", "ZW", "BJ", "MG", "MU", "MZ", "AO", "CI", "DJ", "ZM", "CD", "CG", "IQ", "LY", "TJ", "VE", "ET", "XK"], "disc_number": 1, "duration_ms": 210181, "explicit": true, "external_urls": {"spotify": "https://open.spotify.com/track/6vtO0DInrbvvYagWeaeVyX"}, "href": "https://api.spotify.com/v1/tracks/6vtO0DInrbvvYagWeaeVyX", "id": "6vtO0DInrbvvYagWeaeVyX", "name": "The Look in Your Eyes", "preview_url": "https://p.scdn.co/mp3-preview/6fc7a29f474655e2b01f36d653c1f206f275904b?cid=e44e7b8278114c7db211c00ea273ac69", "track_number": 1, "uri": "spotify:track:6vtO0DInrbvvYagWeaeVyX", "type": "track"}, "deezer": {}, "musicbrainz": {}}	2025-02-19 19:20:59.172123	\N	\N
10	Mayo Wona Kerol	MC Mody	\N	\N	Dokal	\N	0	00:00:00	\N	{"spotify": {}, "deezer": {}, "musicbrainz": {}}	2025-02-19 19:22:09.617028	\N	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: sodav
--

COPY public.users (id, username, email, password_hash, is_active, created_at, last_login, role) FROM stdin;
\.


--
-- Name: analytics_data_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.analytics_data_id_seq', 1, false);


--
-- Name: artist_daily_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.artist_daily_id_seq', 1, false);


--
-- Name: artist_monthly_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.artist_monthly_id_seq', 1, false);


--
-- Name: artist_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.artist_stats_id_seq', 1, false);


--
-- Name: detection_daily_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.detection_daily_id_seq', 1, false);


--
-- Name: detection_hourly_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.detection_hourly_id_seq', 1, false);


--
-- Name: detection_monthly_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.detection_monthly_id_seq', 1, false);


--
-- Name: radio_stations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.radio_stations_id_seq', 47, true);


--
-- Name: report_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.report_subscriptions_id_seq', 1, false);


--
-- Name: reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.reports_id_seq', 1, false);


--
-- Name: station_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.station_stats_id_seq', 1, false);


--
-- Name: station_track_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.station_track_stats_id_seq', 1, false);


--
-- Name: track_daily_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.track_daily_id_seq', 1, false);


--
-- Name: track_detections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.track_detections_id_seq', 10, true);


--
-- Name: track_monthly_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.track_monthly_id_seq', 1, false);


--
-- Name: track_stats_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.track_stats_id_seq', 1, false);


--
-- Name: tracks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.tracks_id_seq', 10, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sodav
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: analytics_data analytics_data_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.analytics_data
    ADD CONSTRAINT analytics_data_pkey PRIMARY KEY (id);


--
-- Name: artist_daily artist_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.artist_daily
    ADD CONSTRAINT artist_daily_pkey PRIMARY KEY (id);


--
-- Name: artist_monthly artist_monthly_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.artist_monthly
    ADD CONSTRAINT artist_monthly_pkey PRIMARY KEY (id);


--
-- Name: artist_stats artist_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.artist_stats
    ADD CONSTRAINT artist_stats_pkey PRIMARY KEY (id);


--
-- Name: detection_daily detection_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.detection_daily
    ADD CONSTRAINT detection_daily_pkey PRIMARY KEY (id);


--
-- Name: detection_hourly detection_hourly_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.detection_hourly
    ADD CONSTRAINT detection_hourly_pkey PRIMARY KEY (id);


--
-- Name: detection_monthly detection_monthly_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.detection_monthly
    ADD CONSTRAINT detection_monthly_pkey PRIMARY KEY (id);


--
-- Name: radio_stations radio_stations_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.radio_stations
    ADD CONSTRAINT radio_stations_pkey PRIMARY KEY (id);


--
-- Name: report_subscriptions report_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.report_subscriptions
    ADD CONSTRAINT report_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: station_stats station_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_stats
    ADD CONSTRAINT station_stats_pkey PRIMARY KEY (id);


--
-- Name: station_track_stats station_track_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_track_stats
    ADD CONSTRAINT station_track_stats_pkey PRIMARY KEY (id);


--
-- Name: track_daily track_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_daily
    ADD CONSTRAINT track_daily_pkey PRIMARY KEY (id);


--
-- Name: track_detections track_detections_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_detections
    ADD CONSTRAINT track_detections_pkey PRIMARY KEY (id);


--
-- Name: track_monthly track_monthly_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_monthly
    ADD CONSTRAINT track_monthly_pkey PRIMARY KEY (id);


--
-- Name: track_stats track_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_stats
    ADD CONSTRAINT track_stats_pkey PRIMARY KEY (id);


--
-- Name: tracks tracks_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.tracks
    ADD CONSTRAINT tracks_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_radio_stations_id; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_radio_stations_id ON public.radio_stations USING btree (id);


--
-- Name: ix_radio_stations_name; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_radio_stations_name ON public.radio_stations USING btree (name);


--
-- Name: ix_reports_id; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_reports_id ON public.reports USING btree (id);


--
-- Name: ix_track_detections_detected_at; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_track_detections_detected_at ON public.track_detections USING btree (detected_at);


--
-- Name: ix_track_detections_station_id; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_track_detections_station_id ON public.track_detections USING btree (station_id);


--
-- Name: ix_track_detections_track_id; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_track_detections_track_id ON public.track_detections USING btree (track_id);


--
-- Name: ix_tracks_artist; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_tracks_artist ON public.tracks USING btree (artist);


--
-- Name: ix_tracks_label; Type: INDEX; Schema: public; Owner: sodav
--

CREATE INDEX ix_tracks_label ON public.tracks USING btree (label);


--
-- Name: report_subscriptions report_subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.report_subscriptions
    ADD CONSTRAINT report_subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: reports reports_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: station_stats station_stats_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_stats
    ADD CONSTRAINT station_stats_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.radio_stations(id);


--
-- Name: station_track_stats station_track_stats_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_track_stats
    ADD CONSTRAINT station_track_stats_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.radio_stations(id);


--
-- Name: station_track_stats station_track_stats_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.station_track_stats
    ADD CONSTRAINT station_track_stats_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: track_daily track_daily_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_daily
    ADD CONSTRAINT track_daily_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: track_detections track_detections_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_detections
    ADD CONSTRAINT track_detections_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.radio_stations(id);


--
-- Name: track_detections track_detections_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_detections
    ADD CONSTRAINT track_detections_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: track_monthly track_monthly_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_monthly
    ADD CONSTRAINT track_monthly_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: track_stats track_stats_track_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sodav
--

ALTER TABLE ONLY public.track_stats
    ADD CONSTRAINT track_stats_track_id_fkey FOREIGN KEY (track_id) REFERENCES public.tracks(id);


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: sodav
--

ALTER DEFAULT PRIVILEGES FOR ROLE sodav IN SCHEMA public GRANT ALL ON TABLES TO sodav;


--
-- PostgreSQL database dump complete
--

