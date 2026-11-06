#include "raylib.h"
#include "game.hpp"
#include <filesystem>
#include <fstream>
#include <cstdlib>
#include <string>

// Store progress per user instead of requiring write access beside the executable.
std::filesystem::path scorePath() {
#ifdef _WIN32
    const char* root=std::getenv("LOCALAPPDATA");
#else
    const char* root=std::getenv("XDG_DATA_HOME");
    if(!root) { const char* home=std::getenv("HOME"); if(home) return std::filesystem::path(home)/".local/share/star-runner/best.txt"; }
#endif
    return (root?std::filesystem::path(root):std::filesystem::temp_directory_path())/"star-runner/best.txt";
}
void saveBest(int best) {
    try { const auto path=scorePath(); std::filesystem::create_directories(path.parent_path()); std::ofstream(path)<<best; } catch(...) { /* Gameplay works without writable storage. */ }
}
int main() {
    SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT);
    InitWindow(960,600,"Star Runner - C++ Edition");
    SetWindowMinSize(640,400); SetTargetFPS(120); SetExitKey(KEY_NULL);
    RenderTexture2D scene=LoadRenderTexture(960,600);
    SetTextureFilter(scene.texture,TEXTURE_FILTER_BILINEAR);
    runner::Game game;
    try { std::ifstream(scorePath())>>game.best; game.best=std::max(0,game.best); } catch(...) {}
    const Color mint={125,242,202,255}, gold={255,213,120,255}, red={234,113,140,255};
    Vector2 stars[100]; for(auto& s:stars) s={float(GetRandomValue(0,960)),float(GetRandomValue(0,600))};
    int saved=game.best;
    while(!WindowShouldClose()) {
        const float scale=std::min(GetScreenWidth()/960.0f,GetScreenHeight()/600.0f);
        const float ox=(GetScreenWidth()-960*scale)/2,oy=(GetScreenHeight()-600*scale)/2;
        const Vector2 mouse={(GetMouseX()-ox)/scale,(GetMouseY()-oy)/scale};
        const Rectangle button={340,355,280,58};
        if(!IsWindowFocused() && game.state==runner::State::Playing) game.pause();
        if(IsKeyPressed(KEY_P)||IsKeyPressed(KEY_ESCAPE)) game.pause();
        if(game.state!=runner::State::Playing && (IsKeyPressed(KEY_ENTER)||(IsMouseButtonPressed(MOUSE_BUTTON_LEFT)&&CheckCollisionPointRec(mouse,button)))) {
            if(game.state==runner::State::Paused) game.pause(); else game.start();
        }
        const float dx=float(IsKeyDown(KEY_D)||IsKeyDown(KEY_RIGHT))-float(IsKeyDown(KEY_A)||IsKeyDown(KEY_LEFT));
        const float dy=float(IsKeyDown(KEY_S)||IsKeyDown(KEY_DOWN))-float(IsKeyDown(KEY_W)||IsKeyDown(KEY_UP));
        game.update(GetFrameTime(),dx,dy);
        if(game.state==runner::State::Over && game.best>saved) { saveBest(game.best); saved=game.best; }
        BeginTextureMode(scene); ClearBackground({9,16,35,255});
        for(const auto& s:stars) DrawCircleV({s.x,std::fmod(s.y+game.elapsed*24,600.0f)},1.3f,{102,129,175,255});
        for(const auto& o:game.objects) {
            if(o.star) { DrawPoly({o.x,o.y},4,o.radius,float(GetTime()*55),gold); DrawCircleV({o.x,o.y},4,{255,246,211,255}); }
            else { DrawPoly({o.x,o.y},7,o.radius,float(GetTime()*35),red); DrawCircle(int(o.x-5),int(o.y-3),o.radius/4,{157,65,91,255}); }
        }
        DrawTriangle({game.x,game.y-22},{game.x-18,game.y+17},{game.x+18,game.y+17},mint);
        DrawCircle(int(game.x),int(game.y),4,RAYWHITE);
        if(game.state==runner::State::Playing) DrawTriangle({game.x-5,game.y+18},{game.x,game.y+float(GetRandomValue(25,37))},{game.x+5,game.y+18},gold);
        DrawRectangle(0,0,960,72,{12,23,46,255});
        DrawText("STAR RUNNER",24,23,26,mint);
        DrawText(TextFormat("SCORE %04i   BEST %04i",game.score,game.best),570,26,22,RAYWHITE);
        DrawText("ARROWS / WASD   move       P / ESC   pause",24,580,14,{151,171,207,255});
        if(game.state!=runner::State::Playing) {
            DrawRectangle(0,75,960,490,{7,13,29,230});
            std::string heading=game.state==runner::State::Menu?"A LITTLE SHIP. A BIG UNIVERSE.":game.state==runner::State::Paused?"TAKING A SPACE BREAK":"ONE MORE ORBIT?";
            DrawText(heading.c_str(),(960-MeasureText(heading.c_str(),30))/2,230,30,RAYWHITE);
            std::string sub=game.state==runner::State::Over?"Final score: "+std::to_string(game.score):"Collect gold stars. Dodge the asteroids.";
            DrawText(sub.c_str(),(960-MeasureText(sub.c_str(),20))/2,290,20,{164,185,218,255});
            DrawRectangleRounded(button,0.2f,10,mint);
            const char* label=game.state==runner::State::Paused?"RESUME  [ENTER]":"LET'S FLY  [ENTER]";
            DrawText(label,(960-MeasureText(label,22))/2,374,22,{8,35,29,255});
        }
        EndTextureMode();
        BeginDrawing(); ClearBackground(BLACK);
        DrawTexturePro(scene.texture,{0,0,960,-600},{ox,oy,960*scale,600*scale},{0,0},0,WHITE);
        EndDrawing();
    }
    saveBest(game.best); UnloadRenderTexture(scene); CloseWindow(); return 0;
}
