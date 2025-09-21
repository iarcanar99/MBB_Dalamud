using System;
using System.Numerics;
using Dalamud.Interface.Windowing;
using Dalamud.Bindings.ImGui;

namespace DalamudMBBBridge
{
    public class MBBConfigWindow : Window, IDisposable
    {
        private DalamudMBBBridge plugin;

        public MBBConfigWindow(DalamudMBBBridge plugin) : base("🌉 Mgicite Babel v1.4.10.4 Thai Version###MBBBridge")
        {
            this.SizeConstraints = new WindowSizeConstraints
            {
                MinimumSize = new Vector2(450, 350),
                MaximumSize = new Vector2(800, 600)
            };

            this.plugin = plugin;
            this.IsOpen = false;
        }

        public void Dispose()
        {
            // Clean up resources if needed
        }

        public override void Draw()
        {
            var mbbRunning = plugin.CheckMBBProcess();
            var connectionStatus = plugin.IsConnected ? "🟢 Connected" : "🟡 Waiting for connection";
            var mbbStatus = mbbRunning ? "🟢 Running" : "🔴 Not Running";

            // Status Section
            ImGui.TextColored(new Vector4(0.2f, 0.8f, 1.0f, 1.0f), "📊 Status");
            ImGui.Separator();
            ImGui.Spacing();

            ImGui.Text($"Bridge Status: {connectionStatus}");
            ImGui.Text($"MBB Application: {mbbStatus}");
            ImGui.Text($"Messages in Queue: {plugin.MessageQueueCount}");

            ImGui.Spacing();
            ImGui.Spacing();

            // Control Section
            ImGui.TextColored(new Vector4(1.0f, 0.8f, 0.2f, 1.0f), "🎮 Controls");
            ImGui.Separator();
            ImGui.Spacing();

            if (!mbbRunning)
            {
                ImGui.PushStyleColor(ImGuiCol.Button, new Vector4(0.2f, 0.8f, 0.2f, 1.0f));
                ImGui.PushStyleColor(ImGuiCol.ButtonHovered, new Vector4(0.3f, 0.9f, 0.3f, 1.0f));
                ImGui.PushStyleColor(ImGuiCol.ButtonActive, new Vector4(0.1f, 0.7f, 0.1f, 1.0f));

                if (ImGui.Button("🚀 Launch MBB Application", new Vector2(-1, 40)))
                {
                    plugin.LaunchMBB();
                }

                ImGui.PopStyleColor(3);

                ImGui.Spacing();
                ImGui.TextColored(new Vector4(1.0f, 0.4f, 0.4f, 1.0f), "⚠️ MBB is not running");
            }
            else
            {
                ImGui.TextColored(new Vector4(0.4f, 1.0f, 0.4f, 1.0f), "✅ MBB is running normally");
                ImGui.Spacing();

                if (ImGui.Button("🔄 Refresh Status", new Vector2(-1, 30)))
                {
                    plugin.RefreshMBBStatus();
                }
            }

            ImGui.Spacing();
            ImGui.Spacing();

            // Connection Details
            if (plugin.IsConnected)
            {
                ImGui.TextColored(new Vector4(0.4f, 1.0f, 0.4f, 1.0f), "🔗 Bridge Connection Active");
                ImGui.Text("Real-time text capture is working.");
            }
            else
            {
                ImGui.TextColored(new Vector4(1.0f, 0.6f, 0.2f, 1.0f), "⏳ Waiting for MBB Connection");
                ImGui.Text("Start MBB with Dalamud Mode enabled.");
            }

            ImGui.Spacing();
            ImGui.Spacing();

            // Instructions Section
            ImGui.TextColored(new Vector4(0.8f, 1.0f, 0.8f, 1.0f), "📋 Setup Instructions");
            ImGui.Separator();
            ImGui.Spacing();

            ImGui.TextWrapped("1. Launch MBB if not running (use button above)");
            ImGui.TextWrapped("2. Enable 'Dalamud Mode' in MBB Settings");
            ImGui.TextWrapped("3. Press F9 to start translation");
            ImGui.TextWrapped("4. Talk to NPCs for real-time translation");

            ImGui.Spacing();
            ImGui.Spacing();

            // Footer with Commands
            ImGui.Separator();
            ImGui.TextColored(new Vector4(0.7f, 0.7f, 0.7f, 1.0f), "Commands:");
            ImGui.SameLine();
            ImGui.Text("/mbb status");
            ImGui.SameLine();
            ImGui.Text("|");
            ImGui.SameLine();
            ImGui.Text("/mbb launch");
            ImGui.SameLine();
            ImGui.Text("|");
            ImGui.SameLine();
            ImGui.Text("/mbb help");
        }
    }
}