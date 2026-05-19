-- octoflash backend — DDL snapshot
-- Auto-generated from pg_dump --schema-only against the live dev DB.
-- Source of truth is Alembic (alembic/versions/*); regenerate this file with:
--   PGPASSWORD=octoflash pg_dump --schema-only --no-owner --no-privileges \
--     -h 127.0.0.1 -p 5433 -U octoflash -d octoflash_db > sql/schema.sql

--
-- PostgreSQL database dump
--

\restrict bnE8o4KGunG8DIrDwmrCMpBvlcNtpcQedoIs2B57OY22ePax3dw6uGbbNnlLGgu

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg13+1)
-- Dumped by pg_dump version 17.9 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: channel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.channel (
    id character varying NOT NULL,
    platform character varying(32) NOT NULL,
    source_url text NOT NULL,
    external_id character varying(128),
    handle character varying(128),
    name character varying(255) NOT NULL,
    description text,
    thumbnail_url text,
    subscriber_count bigint,
    accent_color character varying(16),
    last_synced_at timestamp with time zone,
    owner_id character varying,
    is_deleted boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: channel_video; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.channel_video (
    id character varying NOT NULL,
    channel_id character varying NOT NULL,
    external_id character varying(64) NOT NULL,
    source_url text NOT NULL,
    title text NOT NULL,
    description text,
    thumbnail_url text,
    kind character varying(16) NOT NULL,
    duration_seconds integer,
    view_count bigint,
    published_at timestamp with time zone,
    fetched_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job (
    id character varying NOT NULL,
    kind character varying(32) NOT NULL,
    project_id character varying,
    scene_id character varying,
    status character varying(16) NOT NULL,
    progress integer NOT NULL,
    logs jsonb NOT NULL,
    output_url text,
    workflow_id character varying,
    run_id character varying,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    id character varying NOT NULL,
    title character varying(255) NOT NULL,
    source_url text,
    owner_id character varying,
    is_deleted boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: scene; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scene (
    id character varying NOT NULL,
    project_id character varying NOT NULL,
    n integer NOT NULL,
    title character varying(255),
    template character varying(64) NOT NULL,
    params jsonb NOT NULL,
    prompt text,
    duration double precision,
    style character varying(32),
    motion character varying(32),
    status character varying(16) NOT NULL,
    selected_variation_id character varying,
    extra_steps jsonb NOT NULL,
    mode character varying(16) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: scene_instruction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scene_instruction (
    id character varying NOT NULL,
    scene_id character varying NOT NULL,
    instruction text NOT NULL,
    diff jsonb NOT NULL,
    applied_by character varying,
    applied_at timestamp with time zone NOT NULL
);


--
-- Name: variation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.variation (
    id character varying NOT NULL,
    scene_id character varying NOT NULL,
    params_snapshot jsonb NOT NULL,
    video_url text,
    audio_url text,
    duration double precision,
    frame_count integer,
    file_size bigint,
    status character varying(16) NOT NULL,
    rendered_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: workflow_edge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_edge (
    id character varying NOT NULL,
    project_id character varying NOT NULL,
    from_node_id character varying NOT NULL,
    to_node_id character varying NOT NULL,
    kind character varying(16) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: workflow_node; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_node (
    id character varying NOT NULL,
    project_id character varying NOT NULL,
    kind character varying(16) NOT NULL,
    x double precision NOT NULL,
    y double precision NOT NULL,
    w double precision,
    h double precision,
    label character varying(255),
    scene_id character varying,
    style_override character varying(32),
    branch_label character varying(64),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: channel channel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel
    ADD CONSTRAINT channel_pkey PRIMARY KEY (id);


--
-- Name: channel_video channel_video_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_video
    ADD CONSTRAINT channel_video_pkey PRIMARY KEY (id);


--
-- Name: job job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job
    ADD CONSTRAINT job_pkey PRIMARY KEY (id);


--
-- Name: project project_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);


--
-- Name: scene_instruction scene_instruction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene_instruction
    ADD CONSTRAINT scene_instruction_pkey PRIMARY KEY (id);


--
-- Name: scene scene_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene
    ADD CONSTRAINT scene_pkey PRIMARY KEY (id);


--
-- Name: channel_video uq_channel_video_external_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_video
    ADD CONSTRAINT uq_channel_video_external_id UNIQUE (channel_id, external_id);


--
-- Name: scene uq_scene_project_n; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene
    ADD CONSTRAINT uq_scene_project_n UNIQUE (project_id, n);


--
-- Name: variation variation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.variation
    ADD CONSTRAINT variation_pkey PRIMARY KEY (id);


--
-- Name: workflow_edge workflow_edge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_edge
    ADD CONSTRAINT workflow_edge_pkey PRIMARY KEY (id);


--
-- Name: workflow_node workflow_node_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_node
    ADD CONSTRAINT workflow_node_pkey PRIMARY KEY (id);


--
-- Name: ix_channel_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_channel_external_id ON public.channel USING btree (external_id);


--
-- Name: ix_channel_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_channel_owner_id ON public.channel USING btree (owner_id);


--
-- Name: ix_channel_video_channel_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_channel_video_channel_id ON public.channel_video USING btree (channel_id);


--
-- Name: ix_job_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_project_id ON public.job USING btree (project_id);


--
-- Name: ix_job_scene_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_scene_id ON public.job USING btree (scene_id);


--
-- Name: ix_job_workflow_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_workflow_id ON public.job USING btree (workflow_id);


--
-- Name: ix_project_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_project_owner_id ON public.project USING btree (owner_id);


--
-- Name: ix_scene_instruction_scene_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scene_instruction_scene_id ON public.scene_instruction USING btree (scene_id);


--
-- Name: ix_scene_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scene_project_id ON public.scene USING btree (project_id);


--
-- Name: ix_variation_scene_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_variation_scene_id ON public.variation USING btree (scene_id);


--
-- Name: ix_workflow_edge_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_workflow_edge_project_id ON public.workflow_edge USING btree (project_id);


--
-- Name: ix_workflow_node_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_workflow_node_project_id ON public.workflow_node USING btree (project_id);


--
-- Name: channel_video channel_video_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.channel_video
    ADD CONSTRAINT channel_video_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channel(id);


--
-- Name: scene_instruction scene_instruction_scene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene_instruction
    ADD CONSTRAINT scene_instruction_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES public.scene(id);


--
-- Name: scene scene_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scene
    ADD CONSTRAINT scene_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(id);


--
-- Name: variation variation_scene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.variation
    ADD CONSTRAINT variation_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES public.scene(id);


--
-- Name: workflow_edge workflow_edge_from_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_edge
    ADD CONSTRAINT workflow_edge_from_node_id_fkey FOREIGN KEY (from_node_id) REFERENCES public.workflow_node(id);


--
-- Name: workflow_edge workflow_edge_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_edge
    ADD CONSTRAINT workflow_edge_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(id);


--
-- Name: workflow_edge workflow_edge_to_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_edge
    ADD CONSTRAINT workflow_edge_to_node_id_fkey FOREIGN KEY (to_node_id) REFERENCES public.workflow_node(id);


--
-- Name: workflow_node workflow_node_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_node
    ADD CONSTRAINT workflow_node_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(id);


--
-- Name: workflow_node workflow_node_scene_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_node
    ADD CONSTRAINT workflow_node_scene_id_fkey FOREIGN KEY (scene_id) REFERENCES public.scene(id);


--
-- PostgreSQL database dump complete
--

\unrestrict bnE8o4KGunG8DIrDwmrCMpBvlcNtpcQedoIs2B57OY22ePax3dw6uGbbNnlLGgu

