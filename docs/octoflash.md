 What the MVP does                                                                                                                                                                                    
   
  Single linear pipeline (FastAPI app, ~30 endpoints):                                                                                                                                                 
  paste YouTube URL → download (yt-dlp) → extract frames + transcript                                                                                                                                
    → Claude (vision + text) writes FULL Manim Python script         
    → manim-voiceover (ElevenLabs) renders Scene with narration                                                                                                                                        
    → evaluate output, self-correct if quality < 7/10                                                                                                                                                  
    → watermark intro/outro → distribute (TikTok / YouTube / IG / LinkedIn)                                                                                                                            
                                                                                                                                                                                                       
  Key MVP services we could lift: downloader.py (yt-dlp), frame_extractor.py (ffmpeg keyframes), transcriber.py (youtube-transcript-api + faster-whisper fallback), prompt_builder.py (assembles Claude
   input), script_generator.py (Claude → raw Manim code), voices.py (ElevenLabs), watermark logic in renderer.py, the 5 platform uploaders, auto_processor.py (pipeline orchestrator).                 
                                                                                                                                                                                                       
  What's NOT in the MVP: Medium, Substack, or any article scraping. The new ask expands input sources beyond YouTube.                                                                                  
                                                                
  How it differs from our current backend                                                                                                                                                              
                                                                
  ┌─────────────────┬───────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────┐
  │                 │                        MVP                        │                               Our backend                                │
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
  │ Authoring model │ Claude writes raw Manim Python per scene          │ Config-driven: Claude picks templates from a catalog, primitives compose │
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤
  │ Editability     │ Output is a Python file — hard to edit after      │ Scene = (template_id, params) — every field tweakable in the inspector   │                                                   
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤                                                   
  │ Determinism     │ Re-running same prompt → different code each time │ Same (template, params) → identical render every time                    │                                                   
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤                                                   
  │ Voiceover       │ First-class (manim-voiceover + ElevenLabs)        │ Not wired — no audio anywhere                                            │
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤                                                   
  │ Self-correction │ Render → score → regenerate loop                  │ None; assumes first render is acceptable                                 │
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤                                                   
  │ Distribution    │ 4 platform uploaders                              │ None                                                                     │
  ├─────────────────┼───────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────┤                                                   
  │ Source types    │ YouTube only                                      │ YouTube (channels feature)                                               │
  └─────────────────┴───────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────┘                                                   
                                                                
  Recommended adaptation — option C: "Templatize the MVP"                                                                                                                                              
   
  Don't replace our scene/template/primitive system. Instead, feed source content into the planner we already have.                                                                                    
                                                                
  paste URL → identify source type → fetch content →                                                                                                                                                   
    Claude planner produces ordered list of SceneSpec (using existing templates) →
    PlannerService.plan_from_prompt or plan_from_transcript →                                                                                                                                          
    create Project + Scenes (existing flow) →                                                                                                                                                          
    user reviews/edits in inspector (existing UX) →                                                                                                                                                    
    render → preview → export (existing pipeline)                                                                                                                                                      
                                                                
  This keeps the scene-first editable thesis, reuses everything we built, and adds three small content-fetcher services + one new endpoint.                                                            
                                                                
  New pieces to build:                                                                                                                                                                                 
  1. SourceFetcherService (or three: youtube_transcript_service, article_scraper_service, frame extraction). Decides per-URL which fetcher to invoke. Returns {text, optional_frames, source_metadata}.
  2. MediumArticleScraper — Medium has loose anti-scraping but requests + BeautifulSoup + a UA works for public articles.                                                                              
  3. SubstackArticleScraper — Substack RSS gives clean content; or scrape /p/<slug> page.                                
  4. YouTubeTranscriptService — try youtube-transcript-api first (free, fast), Whisper fallback for videos without captions.                                                                           
  5. Extend PlannerService.plan_from_transcript (currently NotImplementedError) to accept the fetched text + optional frames.                                                                          
  6. New endpoint: POST /projects/from-source { source_url, title?, style_preference? } — fetches → plans → creates Project with N scenes → returns ProjectDetail.                                     
                                                                                                                                                                                                       
  What we deliberately drop from the MVP (for now):                                                                                                                                                    
  - Raw-Manim-from-Claude path (we're committed to templates)                                                                                                                                          
  - Self-correction loop (templates remove most failure modes Claude introduced)                                                                                                                       
  - ElevenLabs voiceover (out of MVP scope, separate add-on)                                                                                                                                           
  - Platform uploaders (out of scope)                                                                                                                                                                  
  - Watermarking (cosmetic, easy to add later as a primitive)   
                                                                                                                                                                                                       
  Questions before I build                                                                                                                                                                             
                                                                                                                                                                                                       
⏺ User answered Claude's questions:                                                                                                                                                                    
  ⎿  · Endpoint shape for source-driven project creation? → New `POST /projects/from-source` (recommended)                                                                                             
     · Sync or async ingest? Article scrape is fast; YouTube + transcribe can be slow. → Sync for articles, Temporal workflow for video (recommended)                                                  
     · Source types to ship in v1? → YouTube long-form (existing channel videos + arbitrary URLs), YouTube shorts (vertical, < 60s), Medium articles, Substack articles
     · Visual content for Claude — frames or text-only? → Text + key frames (mirrors MVP)                                                                                                              
                                                                                     
⏺ All four decisions locked. This is a multi-day build — I'm proposing a phased rollout so each phase leaves the system runnable + lets you smoke-test before the next.
                                                                                                       
  Build plan                                                                                                                                                                                           
                              
  Phase 1 — Infra + endpoint shell (~20 min)                                                                                                                                                           
  - Add deps (youtube-transcript-api, beautifulsoup4, feedparser, lxml, pillow for frame compression)                                                                                                
  - SourceFetcherService dispatcher (URL → source type)                                                                                                                                                
  - POST /projects/from-source endpoint — returns 501 per source type for now                                                                                                                          
  - pyproject.toml + app/service/source_fetcher_service.py + new request/response types + endpoint scaffolding                                                                                         
                                                                                                                                                                                                       
  Phase 2 — Articles (Medium + Substack), sync (~45 min)                                                                                                                                               
  - ArticleScraperService (Medium: requests + BeautifulSoup with UA; Substack: try RSS then HTML)                                                                                                      
  - PlannerService.plan_from_source(text=..., frames=None) — text-only flow                                                                                                                            
  - POST /projects/from-source for article URLs → fetch → plan → create project + scenes → return ProjectDetail
  - Smoke test with a real Medium + Substack URL                                                                                                                                                       
                                                                                                                                                                                                       
  Phase 3 — YouTube text-only (~45 min)                                                                                                                                                                
  - TranscriptService — youtube-transcript-api first (free, instant), faster-whisper fallback                                                                                                          
  - Wire YouTube long/shorts URLs through the dispatcher → transcript → existing plan_from_source (still text-only)                                                                                    
  - Still sync for now to validate the path                                                                        
  - Smoke test with a real YouTube short                                                                                                                                                               
                                                                                                                                                                                                       
  Phase 4 — Add keyframes (vision) (~30 min)                                                                                                                                                           
  - KeyframeExtractorService — ffmpeg pulls N evenly-spaced frames + Pillow downscales to ~768px for Claude                                                                                            
  - Extend PlannerService.plan_from_source to accept frames → multimodal Claude call                                                                                                                   
  - Backfill into the YouTube path                                                                                                                                                                     
  - Smoke test — compare scene plan with frames vs without                                                                                                                                             
                                                                
  Phase 5 — Async YouTube via Temporal (~45 min)                                                                                                                                                       
  - IngestYouTubeSourceWorkflow — activities for download / transcribe / keyframes / plan / create scenes
  - YouTube paths now async (return 202 + Job; FE polls)                                                                                                                                               
  - Articles stay sync                                          
  - Smoke test end-to-end                                                                                                                                                                              
                                                                
  ~3-4 hours total. Each phase ships independently working.                                                                                                                                            
                                                                                                                                                                                                       
  Starting Phase 1 now unless you want a different order or smaller initial scope.      
  

⏺ Phase 1 complete. Each source type returns the correct envelope:                                                                                                                                     
  - YouTube long & shorts → 501 with "Phase 3" hint                                                                                                                                                    
⏺ Phase 2: article scrapers + source-driven planner + wire the Medium/Substack branches.




 Phase 2 done — both Medium and Substack work end-to-end.                                                                                                                                             
                                                                                                                                                                                                       
  Substack:  20s  → 5 scenes  (article 37KB)                                                                                                                                                           
  Medium:    16s  → 4 scenes  (LLM intro article)                                                                                                                                                      
                                                                                                                                                                                                       
  Both produce templated, ordered scenes from real-world content. Source type auto-detected. Template validation kicks in (only implemented templates proposed). Reasoning string captured.            
                                                                
  What landed in Phase 2:                                                                                                                                                                              
  - app/service/article_scraper_service.py — Medium (BeautifulSoup) + Substack (RSS → HTML fallback)
  - app/service/source_fetcher_service.py — _fetch_medium + _fetch_substack wired                                                                                                                      
  - app/service/planner_prompts.py — new build_source_messages + _SOURCE_SYSTEM prompt tailored for long-form distillation
  - app/service/planner_service.py — new plan_from_source(text, …) method                                                                                                                              
  - app/service/project_service.py — create_from_source Medium/Substack branch fully wired                                                                                                             
                                                                                                                                                                                                       
  One thing to note: Substack URLs in the wild often use custom domains (e.g. noahpinion.blog). The classifier currently requires *.substack.com. Substack URLs DO 301-redirect from                   
  *.substack.com/p/... to the custom domain (and the scrape follows it correctly), so pasting the substack.com URL works. If users paste the custom-domain URL directly, the classifier will reject. We
   can either:                                                                                                                                                                                         
  - Add an HTTP probe step (slow, complex) to detect Substack on custom domains                                                                                                                        
  - Document that users should use the *.substack.com URL                      
  - Add a fallback "unknown URL → try as Substack" path  
                                                                                                                                                                                                       
  Worth flagging for later but doesn't block Phase 3.  
  


⏺ Phase 3 done — YouTube → captions → Claude plan → 5 scenes in 19s.                                                                                                                                                                                                                                                                                                                                                              
   
  Title auto-populated from the video metadata: "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster)". Claude correctly distilled the lyrics:                                                                                                                                                                                                                                                                    
  - title_reveal "Opening Hook"                                 
  - big_quote "The Promise"                                                                                                                                                                                                                                                                                                                                                                                                       
  - word_swap "The Six Promises"                                
  - highlight_marker "Emotional Core"                                                                                                                                                                                                                                                                                                                                                                                             
  - text_pop "Final Statement"                                  

  Full state across phases:                                                                                                                                                                                                                                                                                                                                                                                                       
   
  ┌───────────────────┬──────────────────────────────────────────────────┬──────────────────────────────────────────────────┐                                                                                                                                                                                                                                                                                                     
  │      Source       │                Endpoint behavior                 │                     Verified                     │
  ├───────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Medium article    │ Sync, ~16s                                       │ ✓                                                │
  ├───────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Substack article  │ Sync, ~20s                                       │ ✓                                                │                                                                                                                                                                                                                                                                                                     
  ├───────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ YouTube long-form │ Sync, ~19s (captions); slower (Whisper fallback) │ ✓                                                │                                                                                                                                                                                                                                                                                                     
  ├───────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────────┤                                                                                                                                                                                                                                                                                                     
  │ YouTube shorts    │ Same as long-form                                │ ✓ (path works, depends on captions availability) │
  ├───────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────────────────────┤                                                                                                                                                                                                                                                                                                     
  │ Unsupported URL   │ 400                                              │ ✓                                                │
  └───────────────────┴──────────────────────────────────────────────────┴──────────────────────────────────────────────────┘                                                                                                                                                                                                                                                                                                     
                                                                
  Key fix made during Phase 3: swapped youtube-transcript-api (was returning empty XML from YouTube's bot-throttling) for yt-dlp subtitle download — significantly more reliable. Whisper still wired as the final fallback for videos without captions.                                                                                                                                                                          
   
  What's still ahead:                                                                                                                                                                                                                                                                                                                                                                                                             
  - Phase 4 — keyframes for Claude vision (richer scene planning when text isn't enough)
  - Phase 5 — move YouTube path off the sync request, onto a Temporal workflow                                                                                                                                                                                                                                                                                                                                                    
                                                                              
  Phase 4 or pause?                                                                                                                                                                                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                                                                                                                                                                                                  
✻ Brewed for 18m 40s · 3 shells still running                                                                                                                                                                                                                                                                                                                                                                                     
                                                                                                                                                                                                                                                                                                                                                                                                                                  
❯  Phase 4 or pause?                                                                                                                                                                                                                                                                                                                                                                                                              

  So: (a) pause, (b) Phase 5 (async), or (c) Phase 4 anyway if you want feature parity with the MVP.


Skip 4 do 5


⏺ Phase 5 done. Worker is killable; both processes are in the background.
                                                                                           
  Async YouTube ingest, working end-to-end:                                                                                                                                                                                                                                                                                                                                                                                       
                                                                                                                                                                                                                                                                                                                                                                                                                                  
  request returns in 0s with { project, job: { status: queued, workflow_id } }                                                                                                                                                                                                                                                                                                                                                    
              │                                                                                                                                                                                                                                                                                                                                                                                                                   
              ▼  (worker picks up workflow on Temporal Cloud)                                                                                                                                                                                                                                                                                                                                                                     
  [ 3s] running p=35   ← fetched: captions, 2066 chars                                                                                                                                                                                                                                                                                                                                                                            
  [ 6s] running p=35                                                                                                                                                                                                                                                                                                                                                                                                              
  [ 9s] running p=35                                                                                                                                                                                                                                                                                                                                                                                                              
  [12s] running p=35   ← planning (Claude tool_use)                                                                                                                                                                                                                                                                                                                                                                               
  [15s] done    p=100  ← scenes persisted, project title updated                                                                                                                                                                                                                                                                                                                                                                  
                                                                                                                                                                                                                                                                                                                                                                                                                                  
  Job logs end up structured:
  - step=started (source_url)                                                                                                                                                                                                                                                                                                                                                                                                     
  - step=fetched (title, text_chars, transcript_source)                                                                                                                                                                                                                                                                                                                                                                           
  - step=planned (scene_count)                         
  - step=done (scene_ids, title_updated)                                                                                                                                                                                                                                                                                                                                                                                          
                                                                
  Final state: project title set from video metadata, 5 scenes created via the planner — same templates the sync path produced before.                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                                                                                                  
  What changed:
  - app/workers/activities/ingest_activity.py — 3 new activities (fetch_source, plan_from_source, persist_ingest) + dataclass payloads                                                                                                                                                                                                                                                                                            
  - app/workers/workflows/ingest_workflow.py — IngestFromSourceWorkflow orchestrating them with retry policies + per-step Job updates                                                                                                                                                                                                                                                                                             
  - app/workers/{workflows,activities}/__init__.py — registered new workflow + activities                                            
  - app/service/project_service.py — YouTube branch now creates a Job, starts the workflow, and returns 202-shape with job populated; articles still sync                                                                                                                                                                                                                                                                         
                                                                                                                                                                                                                                                                                                                                                                                                                                  
  Articles unchanged (Medium/Substack still sync — ~16-20s is fine for the request lifecycle).                                                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                                                                                                                                                  
  Knock-on: the kept-around TranscribeSourceWorkflow stub is now dead code (its responsibility is fully subsumed by the ingest workflow). Worth deleting if you want, but it's harmless to leave for now.                                                                                                                                                                                                                         
                                                                                                                                                                                                                                                                                                                                                                                                                                  
  Pause, or commit these changes?                                                                                                                         


  Port plan — dependency order

  Going leaf → root so each port has its prerequisites:

  Week 1 — minimum to render one MP4 end-to-end

  1. Bulk copy (no adaptation, they're pure Manim code or static assets):
    - manim_pipeline/{visual_effects,ml_visuals,plot_patterns,diagram_patterns,math_animations}.py → app/manim_pipeline/ in new repo
    - manim_ce_*.py + manim_math_*.py + manim_plot_reference.py → app/manim_pipeline/_references/ (system-prompt fodder)
    - styles.py (OctoflashScene + watermark + voice service setup) — small adaptation for env vars
    - voices.py — copy as-is
  2. Port-and-adapt (the brain):
    - services/prompt_builder.py → app/service/prompt_builder_service.py (sync, small)
    - services/script_generator.py → app/service/script_generator_service.py (async-ify the Anthropic streaming; keep all 25+ sanitizers verbatim)
    - manim_pipeline/renderer.py → split into app/service/manim_render_service.py (the subprocess + fallback chain) and keep the iterative-improvement loop alongside
    - services/{frame_extractor,describer}.py → app/service/{frame_extractor,describer}_service.py
    - Scene.template/params/extra_steps → Scene.prompt + script_code + voice_id + duration_seconds (matches MVP's videos doc plus per-clip granularity)
    - Add Project columns: orientation, voice_id, target_duration, transcript, description, manim_prompt, status
    - One Alembic migration
  4. Workflow rewiring
    - Extend existing IngestFromSourceWorkflow: after fetch, add extract_frames_activity → describe_activity → build_prompt_activity → write brief to Project, mark status=analyzed (no scenes yet)
    - New GenerateVideoWorkflow: script_gen_activity → render_activity (with fallback chain inside the activity) → optional evaluate_loop_activity → write Scene.script_code + S3 URL. status=generated.
    - Treat the whole video as one Scene initially (matches MVP exactly). Single MP4 output.
  5. Smoke test: paste the same Rick Astley URL → end-to-end → MP4 on disk.

  Week 2 — split into clips + editor
  - Plan-into-N-clips activity (Claude segments the brief into clip-sized chunks)
  - Per-clip script_code + per-clip render
  - ffmpeg concat at preview/export time
  - Workflow-DAG API for the editor
  - Per-clip prompt edit → re-render only that clip

  Week 3 — publishing
  - Port youtube_uploader.py, youtube_metadata.py, OAuth flow

  Discarded (or deferred indefinitely):
  - 127-template catalog as planning surface — keep file, expose as effect-preset library for clip nodes in editor (week 4+)
  - extra_steps / instruct / template_service / variation_service machinery — wrong abstraction for this product; delete in the refactor
  - manim_runner_service.py (stub) / manim_scene.py (stub) — replaced by the ported manim_render_service
⏺ Phase 1 done. Summary of changes:                     
                                                                                                                                                                                                       
  ┌────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐ 
  │                    File                    │                                                                      Change                                                                       │   
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
  │ core/config.ts                             │ DEFAULT_API_URL → http://localhost:8008                                                                                                           │   
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
  │ core/api/projects.ts                       │ Full rewrite: Project adds status, orientation, quality, voiceover, voice*, target/sourceDuration, transcript, description, manimPrompt,          │   
  │                                            │ framesDir, finalVideoUrl. New fromSource(), generate(), previewUrl(). Drops preview/export POST.                                                  │   
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ core/api/scenes.ts                         │ Full rewrite: SceneResponse matches new shape (scriptCode, scriptCodeHash, voiceIdOverride, videoUrl, renderMethod, evalScore, evalFeedback). New │   
  │                                            │  regenerate() + previewUrl(). Drops variations + selectVariation.                                                                                 │   
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ 
  │ core/api/templates.ts                      │ Stubbed (list() returns [], get() throws) — templates demoted to effect presets, backend endpoints removed.                                       │   
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ core/api/jobs.ts                           │ JobKind documented; kept full union for backward compat.                                                                                          │ 
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ core/api/index.ts                          │ Exports updated (drop variations, add new types).                                                                                                 │ 
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ core/scenes.ts (stub)                      │ SceneStatus → LegacySceneStatus to avoid collision with API type.                                                                                 │ 
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ web/store/projectsStore.ts                 │ Drop selectVariation; remove force from patchScene.                                                                                               │ 
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ web/store/jobsStore.ts                     │ Rewrite: startVariations/Preview/Export → startAnalyze/Generate/Regenerate.                                                                       │ 
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ web/pages/editor/templates.tsx             │ Cast t.glyph as TemplateId (pre-existing type mismatch surfaced by build).                                                                        │ 
  ├────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤   
  │ Backend:                                   │ Added script_code_hash field so FE sees it.                                                                                                       │
  │ app/api/v1/response/scene_response.py      │                                                                                                                                                   │   
  └────────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                                                                                                                                       
  Build state:                                                 
  - ✅ @octoflash/core compiles (tsc clean)
  - ✅ @octoflash/cweb compiles + Vite production build succeeds
  - ✅ @Backend API respmnse shape matches FE TypeScript types 1:1
      B       A   r        s     m       F  T          t     1                                                                                                                                         
  The FE will now compile against the new backend, but existing pages are still stubs — they reference VIDEOS/CHANNELS/etc fixture data, not real API calls. That's Phase 2 (per-clip editor view) and 
  Phase 3 (entry-point flow with URL paste form + voice picker).                                                                                                                                       
                                                                                                                                                                                                       
  Want me to push into Phase 3 next (URL-paste form on the videos page → analyze → see brief → start generate)? That gives you a working entry point with no DAG editor yet.                           
                                                               
✻ Worked for 43m 13s · 1 shell still running                                                                                                                                                           
                                                                             
❯ build an elaborate plan for phase 2 and phase 3                                                                                                                                                      
                                                                                                                                                                                                       
⏺ Here's the elaborate plan. Long but organized — skim the headers, dig into what matters.                                                                                                             
                                                                                                                                                                                                       
  ---                                                                                                                                                                                                  
  Phase 2 — Editor view (/projects/:id)
                                                                                                                                                                                                       
  The page a user lands on after analyze completes and where they spend most of their time. This is where the "atomic per-clip re-render" thesis becomes visible.
                                                                                                                                                                                                       
  What the user sees                                                                                                                                                                                   
                                                                                                                                                                                                       
  ┌─────────────────────────────────────────────────────────────────────┐                                                                                                                              
  │ ← Projects   "CPU vs GPU" [✎]    [analyzed] [Re-analyze] [Generate] │ ← Header
  ├─────────────────────────────────────────────────────────────────────┤                                                                                                                              
  │ ▼ Brief (collapsible)                                                │
  │   Transcript  Description  Manim prompt                              │ ← Tabs                                                                                                                      
  │   [editable textarea / markdown / textarea]                          │
  ├─────────────────────────────────────────────────────────────────────┤                                                                                                                              
  │                                                                      │                                                                                                                             
  │  ┌─Start─┐   ┌─Clip 1─┐   ┌─Clip 2─┐   ┌─Clip 3─┐   ┌─End─┐         │ ← React Flow DAG                                                                                                             
  │  │       │──▶│ ▶ play │──▶│ ▶ play │──▶│ ▶ play │──▶│     │         │   (left-to-right linear)                                                                                                     
  │  └───────┘   │ Hook   │   │ CPU seq│   │ GPU... │   └─────┘         │                                                                                                                              
  │              │ 5s     │   │ 8s     │   │ 9s     │                    │                                                                                                                             
  │              │ ✓ready │   │ ✓ready │   │ ✓ready │                    │                                                                                                                             
  │              └────────┘   └────────┘   └────────┘                    │                                                                                                                             
  │                                                                      │                                                                                                                             
  ├─────────────────────────────────────────────────────────────────────┤                                                                                                                              
  │ ▼ Final video  [▶  ━━━━━━━━━━━━━━━━━━━━━━ 0:32 / 0:51 ]            │ ← <video> = /projects/:id/preview                                                                                             
  └─────────────────────────────────────────────────────────────────────┘                                                                                                                              
                                                  ┌─ When a clip is clicked ─┐
                                                  │ Clip 3: "GPU parallel"    │                                                                                                                        
                                                  │ ┌─[video player]──────┐   │                                                                                                                        
                                                  │ │ <video src=preview> │   │ ← Right sidebar                                                                                                        
                                                  │ └─────────────────────┘   │   (slides in)                                                                                                          
                                                  │ Title: [GPU parallel...]  │                                                                                                                        
                                                  │ Prompt: [textarea...]     │
                                                  │ Duration: [9.0s]          │                                                                                                                        
                                                  │ Voice: [inherit ▾]        │
                                                  │ Eval: ★★★★☆ 4/10          │                                                                                                                        
                                                  │ Feedback: "watermark..."  │                                                                                                                        
                                                  │ ──────────────────────    │                                                                                                                        
                                                  │ ▼ Generated script (RO)   │                                                                                                                        
                                                  │ ──────────────────────    │
                                                  │ [Regenerate clip]         │                                                                                                                        
                                                  └───────────────────────────┘
                                                                                                                                                                                                       
  New files                                                    

  ┌─────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────┐                                                    
  │                  Path                   │                                               Purpose                                               │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ pages/project/index.tsx                 │ Route entry — loads project, lays out header / brief / DAG / final-video / sidebar                  │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ pages/project/project-header.tsx        │ Title (inline-editable), status pill, "Re-analyze" / "Generate" / "Export HD"                       │                                                    
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ pages/project/brief-panel.tsx           │ Collapsible 3-tab panel (Transcript / Description / Manim prompt); textareas with debounced PATCH   │                                                    
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ pages/project/clip-sidebar.tsx          │ Right-side drawer for selected clip — player, prompt editor, eval, script viewer, Regenerate button │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ pages/project/final-video.tsx           │ Bottom bar with <video src={projectsApi.previewUrl(id)}> — only renders when status === "generated" │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ components/workflow/workflow-canvas.tsx │ Wraps React Flow, builds nodes/edges from Project.scenes, handles selection                         │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ components/workflow/clip-node.tsx       │ Custom React Flow node — thumb (first output frame) + title + status badge + duration               │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ components/workflow/status-badge.tsx    │ Color-coded per-clip status indicator (draft / scripting / rendering / ready / failed)              │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ store/editorStore.ts                    │ UI-only state: selectedSceneId, briefOpen, sidebarOpen                                              │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ hooks/use-project-polling.ts            │ When project.status ∈ {analyzing, generating} → setInterval refetch every 3s until terminal         │
  ├─────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────┤                                                    
  │ hooks/use-clip-polling.ts               │ When scene.status ∈ {scripting, rendering} → poll just that scene                                   │
  └─────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────┘                                                    
                                                               
  Components → data flow                                                                                                                                                                               
                                                               
  ProjectPage
    ↓ openProject(id) on mount (Zustand projectsStore)
    ↓ if status ∈ {analyzing, generating} → useProjectPolling hook spins up                                                                                                                            
    │                                                                                                                                                                                                  
    ├─ ProjectHeader  ──→ projectsStore.renameCurrent, jobsStore.startGenerate                                                                                                                         
    ├─ BriefPanel     ──→ projectsStore.patchProject(transcript|description|manimPrompt)                                                                                                               
    ├─ WorkflowCanvas ──→ reads currentProject.scenes; on clip click → editorStore.selectScene(id)                                                                                                     
    ├─ FinalVideo     ──→ <video src={projectsApi.previewUrl(currentProject.id)}>                                                                                                                      
    └─ ClipSidebar (conditional on selectedSceneId)                                                                                                                                                    
         ├─ <video src={scenesApi.previewUrl(sceneId)}>                                                                                                                                                
         ├─ debounced patchScene on prompt edit                                                                                                                                                        
         ├─ Regenerate button → jobsStore.startRegenerate(sceneId)                                                                                                                                     
         └─ on regen done → refetch project → final-video src auto-busts (?t=...)                                                                                                                      
                                                                                                                                                                                                       
  Dependencies to add                                          
                                                                                                                                                                                                       
  "@xyflow/react": "^12"        // React Flow v12 — DAG canvas                                                                                                                                         
  "@tanstack/react-virtual": "?"  // only if scripts/transcripts get huge — defer
                                                                                                                                                                                                       
  Plus lucide-react icons we'll need (Play, Pause, RefreshCw, Sparkles, ChevronRight, Code2) — already in the project.                                                                                 
                                                                                                                                                                                                       
  Order of implementation (so we have something running at every checkpoint)                                                                                                                           
                                                               
  ┌──────┬─────────────────────────────────────────────────────────────────────────────────┬──────┬───────────────────────────────────────────────────────────┐                                        
  │ Step │                                      What                                       │ Time │                        Checkpoint                         │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.1  │ Routing: add /projects/:id route + minimal page skeleton, link from videos page │ 15m  │ Click a project card → URL changes                        │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤
  │ 2.2  │ editorStore + open/load logic (uses existing projectsStore)                     │ 15m  │ Page shows project title + status pill                    │                                        
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.3  │ BriefPanel with read-only transcript/description/manim_prompt                   │ 30m  │ Brief tabs render real data                               │                                        
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.4  │ Install React Flow, basic WorkflowCanvas with linear nodes from scenes          │ 45m  │ DAG shows N clips left-to-right                           │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.5  │ ClipNode custom node with status badge + thumbnail (output_frames first frame)  │ 45m  │ Each node shows real status/title                         │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.6  │ FinalVideo bottom bar — <video> element loading the preview URL                 │ 15m  │ Final stitched video plays                                │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.7  │ ClipSidebar opens on node click; per-clip <video> element loads                 │ 30m  │ Click clip → sidebar shows that clip's video              │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.8  │ Inline-editable prompt + debounced PATCH                                        │ 30m  │ Edit prompt → DB updates silently                         │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.9  │ Regenerate button → startRegenerate + job-progress UI in sidebar                │ 30m  │ Click regen → polling indicator → on done, clip refreshes │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.10 │ useProjectPolling / useClipPolling hooks for in-flight states                   │ 30m  │ Open page while analyzing → updates live                  │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.11 │ Eval score + feedback panel in sidebar                                          │ 15m  │ See score + feedback for each clip                        │
  ├──────┼─────────────────────────────────────────────────────────────────────────────────┼──────┼───────────────────────────────────────────────────────────┤                                        
  │ 2.12 │ Script viewer in sidebar (read-only, syntax-highlighted Python)                 │ 30m  │ Inspect generated Manim code                              │
  └──────┴─────────────────────────────────────────────────────────────────────────────────┴──────┴───────────────────────────────────────────────────────────┘                                        
                                                               
  Subtotal: ~6 hours                                                                                                                                                                                   
                                                               
  Open design decisions

  Some of these meaningfully shape the build. Worth deciding upfront.                                                                                                                                  
   
  1. React Flow version. @xyflow/react@12 (current, more features, better TS) vs reactflow@11 (more StackOverflow answers, sunset). My recommendation: v12.                                            
  2. Clip detail layout. Right sidebar drawer that slides in (Linear / Notion style) vs full-page modal that replaces the canvas vs collapse-the-canvas-and-show-below. Recommend: sidebar drawer —
  keeps the DAG visible for context.                                                                                                                                                                   
  3. DAG editability now or later. Read-only DAG in Phase 2 (positions auto-computed from Scene.n) vs drag-to-reorder from day one. Recommend: read-only for now, drag in Phase 4 — reorder needs
  backend support for atomically renumbering Scene.n which we haven't built.                                                                                                                           
  4. Brief editability scope. All three of (transcript, description, manim_prompt) editable? Or just transcript? They feed forward into per-clip script_gen so edits affect future re-renders.
  Recommend: all three editable, since they're the inputs to subsequent regenerates anyway.                                                                                                            
  5. Thumbnails. Each clip currently has an output_frames/ directory with 12 sampled frames. Should the FE pick frame 6 as the thumb and load via a new endpoint? Or use the clip's MP4 with poster
  attribute generated on-the-fly? Recommend: add GET /scenes/:id/thumbnail endpoint returning frame_0006.jpg — cheap, plays well with React Flow's nodes which don't load videos by default.           
  6. Final-video cache busting after regenerate. After a clip regenerates, the final-video path is the same (/projects/:id/preview) but the underlying file changed. Browser will cache it
  aggressively. Either bust by appending ?t={updatedAt} query param, or set Cache-Control: no-cache on the backend (already done). Recommend: both — ?t= on the client + cache-control on the server.  
                                                               
  ---                                                                                                                                                                                                  
  Phase 3 — Entry-point flow + project list                    
                                                                                                                                                                                                       
  Where the user starts. Less surface area than Phase 2 but more polish since it's the first thing they see.
                                                                                                                                                                                                       
  What the user sees                                           
                                                                                                                                                                                                       
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Videos                                              [+ New video]   │
  ├─────────────────────────────────────────────────────────────────────┤                                                                                                                              
  │  ┌─ Paste a YouTube short, Medium, or Substack URL ───────────┐    │
  │  │ [https://youtube.com/shorts/...                          ▶] │    │                                                                                                                              
  │  └──────────────────────────────────────────────────────────────┘    │
  │  ▼ Render options                                                    │                                                                                                                             
  │  Orientation:  [Portrait] [Landscape]                                │
  │  Voiceover:    [ON ●]                                                │                                                                                                                             
  │  Voice:        Gender [Male ▾]  Accent [American ▾]  [Eric ▾]       │
  │  Length:       Auto / [Override: 90s]                                │                                                                                                                             
  ├─────────────────────────────────────────────────────────────────────┤                                                                                                                              
  │  Filter: [All (12)] [Analyzing (1)] [Generating (2)] [Generated (8)]│                                                                                                                              
  ├─────────────────────────────────────────────────────────────────────┤                                                                                                                              
  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                    │
  │  │ [thumbnail]│  │ [thumbnail]│  │ [thumbnail]│                    │ ← Project cards                                                                                                               
  │  │ CPU vs GPU │  │ Eigenvecs  │  │ Penrose... │                    │                                                                                                                               
  │  │ [generated]│  │ [generating│  │ [analyzing]│                    │                                                                                                                               
  │  │ 5 clips    │  │ ━━━━ 62%  │  │ 0:33...    │                    │                                                                                                                                
  │  └────────────┘  └────────────┘  └────────────┘                    │                                                                                                                               
  └─────────────────────────────────────────────────────────────────────┘                                                                                                                              
                                                                                                                                                                                                       
  New files                                                    
                                                                                                                                                                                                       
  ┌─────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                          Path                           │                                                 Purpose                                                  │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ pages/videos.tsx (rewrite)                              │ Real project list driven by projectsStore.loadProjects(); URL paste form at top; status filters          │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ components/url-paste-form.tsx                           │ Input + render options card; submits via jobsStore.startAnalyze(); redirects to /projects/:id on success │                               
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ components/render-options.tsx                           │ Orientation toggle, voiceover switch, voice picker, length override (controlled component)               │                               
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ components/voice-picker.tsx                             │ Cascading dropdowns: gender → accent → voice; loads from /api/v1/voices                                  │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ components/project-card.tsx (rewrite of video-card.tsx) │ Card for a Project showing title, status pill, source thumb, clip count or progress bar                  │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ components/status-pill.tsx (rewrite)                    │ Color-coded pill mapped to new ProjectStatus union                                                       │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ core/api/voices.ts                                      │ Voices API client (new) — list({gender?, accent?}), listAccents()                                        │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ store/voicesStore.ts                                    │ Caches the catalog — loaded once on first read                                                           │
  ├─────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤                               
  │ hooks/use-projects-list-polling.ts                      │ When any project on the page is in-flight, poll the list every 5s                                        │
  └─────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────┘                               
                                                               
  Updates to existing files                                                                                                                                                                            
                                                               
  ┌────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
  │            File            │                                         Change                                          │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ core/api/index.ts          │ Export voicesApi, Voice type                                                            │
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ pages/videos.tsx           │ Replace VIDEOS stub with projectsStore.projects; replace VideoStatus with ProjectStatus │                                                                             
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤                                                                             
  │ components/site-header.tsx │ "New video" button focuses the URL paste form (or scrolls to top)                       │                                                                             
  ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤                                                                             
  │ App.tsx / routes.tsx       │ Route param: /projects/:id to the new project editor page                               │
  └────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────┘                                                                             
                                                               
  Components → data flow                                                                                                                                                                               
   
  VideosPage                                                                                                                                                                                           
    ↓ projectsStore.loadProjects() on mount                    
    ↓ useProjectsListPolling hook (only if any project is in-flight)
    │                                                                                                                                                                                                  
    ├─ UrlPasteForm
    │    ├─ <Input>                                                                                                                                                                                    
    │    ├─ <RenderOptions>          (controlled; emits an object on submit)
    │    └─ on submit:                                                                                                                                                                                 
    │         jobsStore.startAnalyze({ sourceUrl }) → response.project.id                                                                                                                              
    │         → navigate(`/projects/${id}`)                                                                                                                                                            
    │                                                                                                                                                                                                  
    └─ ProjectGrid                                             
         ├─ <StatusFilterTabs>                                                                                                                                                                         
         └─ {projects.map(p => <ProjectCard p={p} />)}         
              └─ click → navigate(`/projects/${p.id}`)                                                                                                                                                 
   
  Order of implementation                                                                                                                                                                              
                                                               
  ┌──────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────┐   
  │ Step │                                                                                 What                                                                                  │      Time       │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ 3.1  │ core/api/voices.ts + voicesStore                                                                                                                                      │ 20m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ 3.2  │ VoicePicker cascading dropdowns                                                                                                                                       │ 30m             │   
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ 3.3  │ RenderOptions form (orientation, voiceover toggle, voice, length)                                                                                                     │ 30m             │   
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.4  │ UrlPasteForm integrating RenderOptions; submit → startAnalyze → navigate                                                                                              │ 30m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.5  │ Rewrite StatusPill with new ProjectStatus mapping                                                                                                                     │ 15m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.6  │ Rewrite ProjectCard (renamed from video-card)                                                                                                                         │ 30m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.7  │ Rewrite videos.tsx page to use real projectsStore + new card                                                                                                          │ 45m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.8  │ useProjectsListPolling hook                                                                                                                                           │ 20m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.9  │ Status filter tabs wired to projects.filter                                                                                                                           │ 15m             │
  ├──────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤   
  │ 3.10 │ Backend: add Project settable fields to UpdateProjectInput (orientation, voiceover, voiceId, etc.) so the URL paste form can persist them. Backend currently only     │ 30m + 1         │
  │      │ takes title/source_url on PATCH.                                                                                                                                      │ migration       │   
  └──────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────┘
                                                                                                                                                                                                       
  Subtotal: ~4 hours                                                                                                                                                                                   
   
  Open design decisions                                                                                                                                                                                
                                                               
  1. Where the URL paste form lives. Top of /videos page (always visible) vs separate /new route (dedicated). Recommend: top of /videos — paste-and-go is faster, and the project grid below gives     
  immediate visual continuity once the project shows up.
  2. Render options when? Inline below the paste input vs collapsed-by-default with a "More options" toggle vs separate config step after analyze. Recommend: collapsed by default — most users just   
  paste and click; opening shows the dropdowns.                                                                                                                                                        
  3. Voice picker shape. Cascading dropdowns (gender → accent → voice) vs single searchable command-style picker vs card grid. With only ~20 voices in the catalog, recommend: simple single dropdown 
  with grouping by accent (no cascading) — less friction.                                                                                                                                              
  4. Voice/orientation persistence. Should options chosen on the paste form be saved as defaults for the next project? Recommend: save to localStorage for now; user pref in DB later.
  5. Auto-redirect to editor on submit. Yes (current plan) vs stay on /videos with a "view" link in the new project card. Recommend: auto-redirect — once they hit Start they want to watch progress,  
  and the editor page has the polling UI anyway.                                                                                                                                                       
  6. Where do you put a "Create empty project" affordance? Right now POST /projects exists for empty projects (no source). Phase 3 doesn't use it. Recommend: drop it — no UI affordance until we hit a
   use case.                                                                                                                                                                                           
  7. Failed-state UX. When a project is in failed state, what do we show? Just a red pill + the Job error message? Or a retry button that calls from-source again with the same URL? Recommend: retry 
  button in the card.                                                                                                                                                                                  
                                                               
  ---                                                                                                                                                                                                  
  Cumulative time + dependencies                               
                                
  ┌──────────────────────────────┬──────┬─────────────────────────────────────────────────────────────────────────────────────────┐
  │            Phase             │ Time │                                    Hard prerequisite                                    │                                                                    
  ├──────────────────────────────┼──────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Phase 2 (editor view)        │ ~6h  │ None — works against existing backend                                                   │                                                                    
  ├──────────────────────────────┼──────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Phase 3 (entry-point + list) │ ~4h  │ Small backend addition: UpdateProjectInput accepts orientation/voiceover/voiceId fields │                                                                    
  ├──────────────────────────────┼──────┼─────────────────────────────────────────────────────────────────────────────────────────┤                                                                    
  │ Total                        │ ~10h │ Plus backend top-up of update_project for Phase 3 (~30m)                                │                                                                    
  └──────────────────────────────┴──────┴─────────────────────────────────────────────────────────────────────────────────────────┘                                                                    
                                                               
  Phase 2 and Phase 3 are independent — you could ship them in either order or in parallel. Phase 3 needs Phase 2 for the editor to land on after submitting; Phase 2 needs Phase 3 to be reachable    
  beyond direct URL entry. They're symbiotic but not blocking. 
                                                                                                                                                                                                       
  ---                                                          
  Questions to lock in before coding                                                                                                                                                                   
                                                                                                                                                                                                       
⏺ User answered Claude's questions:                                                                                                                                                                    
  ⎿  · Order — which phase to build first? → Phase 2 + 3 in parallel                                                                                                                                   
     · React Flow version → @xyflow/react v12 (Recommended)                                                                                                                                            
     · Clip detail layout → Right sidebar drawer (Recommended)
     · DAG editability scope in Phase 2 → Read-only DAG, click to inspect/edit clip (Recommended)                                                                                                      
                                                                    
⏺ Locked in. Interleaving the two phases — here's the actual execution order optimized for earliest working end-to-end demo (URL paste → list → editor → per-clip player). I'll bias toward the
  "click-through demo" path first; per-clip regenerate + polish land after.                                                                                                          
                                                                                                                                                                                                       
  Interleaved execution order                                                                                                                                                                         
                                                                                                                                                                                                       
  ┌─────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────┬───────┬──────┬─────────────────────────────────────────────┐                   
  │  #  │                                                    Slice                                                    │ Phase │ Time │               Demo checkpoint               │                   
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 1   │ Install @xyflow/react@12; add voicesApi + voicesStore                                                       │ 2+3   │ 20m  │ —                                           │                   
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 2   │ New /projects/:id route + skeleton page (header, status pill)                                               │ 2     │ 20m  │ URL /projects/<id> loads, shows title       │                   
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 3   │ Rewrite /videos page using real projectsStore.loadProjects() + ProjectCard                                  │ 3     │ 45m  │ List shows real projects from DB            │                   
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 4   │ WorkflowCanvas (React Flow with linear nodes from Scene.n)                                                  │ 2     │ 45m  │ DAG renders N clip blocks                   │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 5   │ UrlPasteForm (no options yet, just URL) → startAnalyze → redirect                                           │ 3     │ 30m  │ Paste → list → click → editor demo works    │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 6   │ ClipNode (custom React Flow node) + StatusBadge                                                             │ 2     │ 45m  │ Per-clip status/title visible               │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 7   │ FinalVideo bottom bar with <video src=previewUrl(id)>                                                       │ 2     │ 15m  │ Generated project plays                     │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 8   │ useProjectPolling hook — keeps page live during analyze/generate                                            │ 2     │ 30m  │ Open mid-flight project → updates real-time │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 9   │ ClipSidebar drawer + per-clip <video> + prompt editor (read-only first)                                     │ 2     │ 45m  │ Click clip → sidebar shows + plays clip     │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 10  │ Debounced PATCH on prompt edit + Regenerate button                                                          │ 2     │ 45m  │ Edit + regenerate atomic flow works         │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 11  │ Backend: extend UpdateProjectInput for orientation/voiceover/voice fields                                   │ 3     │ 30m  │ API can save render options                 │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 12  │ RenderOptions (orientation toggle, voiceover, voice picker grouped by accent) — collapsible on UrlPasteForm │ 3     │ 45m  │ Paste form has full options                 │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 13  │ Status filter tabs + polish: localStorage for option defaults, cache-busting query param                    │ 3     │ 30m  │ Pro version of /videos                      │
  ├─────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────┼──────┼─────────────────────────────────────────────┤                   
  │ 14  │ Eval score panel + script viewer in sidebar (read-only Python with prismjs)                                 │ 2     │ 45m  │ Inspect Claude output                       │
  └─────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────┴───────┴──────┴─────────────────────────────────────────────┘                   
                                                               
  Total: ~8 hours interleaved. End-to-end demo (paste → see in list → editor → play) lands at slice 7 (~3.5h in).                                                                                      
                                                               
  Defaults I'm taking on the smaller open questions                                                                                                                                                    
                                                               
  These I'll just do; flag if you want different:                                                                                                                                                      
   
  - Brief editability: all three of transcript / description / manimPrompt are editable textareas. Edits debounced 500ms → PATCH.                                                                      
  - Thumbnails: new GET /scenes/:id/thumbnail backend endpoint returns output_frames/frame_0006.jpg. Falls back to a status-colored placeholder if not yet rendered.
  - Cache busting: ?t={project.updatedAt} query param on the <video src> so a fresh restitch refreshes the player.                                                                                     
  - URL paste form options: collapsed by default ("More options" toggle reveals them).                                                                                                                 
  - Voice picker: single dropdown grouped by accent. Cascading is over-engineering for ~20 voices.                                                                                                     
  - Option persistence: localStorage. DB later.                                                                                                                                                        
  - Auto-redirect on submit: yes — user wants to watch progress immediately.                                                                                                                           
  - No empty-project affordance: drop the "blank project" UI; URL paste is the only entry.                                                                                                             
  - Failed state: red pill + "Retry" button that re-fires fromSource with the stored sourceUrl.                                                                                                        
                                                                                                                                                                                                       
  Heads-up backend change in slice 11                                                                                                                                                                  
                                                                                                                                                                                                       
  Currently PATCH /projects/{id} only accepts title and source_url. To save the user's render options from the paste form, I'll extend UpdateProjectInput to also accept orientation, quality,         
  voiceover, voiceId, voiceGender, voiceAccent, targetDuration. Pure backend touch; no migration needed (columns already exist from task 7).
                                                                                                                                                                                                       
  ---                                                          
  Sound right? Start with slice 1, or do you want to tweak the order / smaller defaults first?
     
