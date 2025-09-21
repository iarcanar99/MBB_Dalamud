using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.IO.Pipes;
using System.Threading.Tasks;
using System.Text;
using System.Text.Json;
using System.Numerics;
using System.Diagnostics;
using Dalamud.Game.Text;
using Dalamud.Game.Text.SeStringHandling;
using Dalamud.Plugin;
using Dalamud.Plugin.Services;
using Dalamud.Game.Command;
using Dalamud.IoC;
using Dalamud.Game.Addon.Lifecycle;
using Dalamud.Game.Addon.Lifecycle.AddonArgTypes;
using FFXIVClientStructs.FFXIV.Component.GUI;
using Dalamud.Memory;
using Dalamud.Interface.Windowing;
using Dalamud.Interface;

namespace DalamudMBBBridge
{
    public sealed class DalamudMBBBridge : IDalamudPlugin
    {
        public string Name => "Mgicite Babel v1.4.10.4 Thai Version by iarcanar";
        private const string CommandName = "/mbb";

        [PluginService] public static IDalamudPluginInterface PluginInterface { get; private set; } = null!;
        [PluginService] public static IChatGui ChatGui { get; private set; } = null!;
        [PluginService] public static ICommandManager CommandManager { get; private set; } = null!;
        [PluginService] public static IPluginLog Log { get; private set; } = null!;
        [PluginService] public static IAddonLifecycle AddonLifecycle { get; private set; } = null!;
        [PluginService] public static IGameGui GameGui { get; private set; } = null!;

        private NamedPipeServerStream? pipeServer;
        private bool isConnected = false;
        private bool isRunning = true;
        private readonly ConcurrentQueue<TextHookData> messageQueue = new();
        private readonly ConcurrentDictionary<string, long> globalMessageHistory = new();
        private string lastTalkMessage = "";
        private string lastSpeaker = "";
        private int lastMessageHash = 0;
        private long lastMessageTime = 0;

        // MBB Process Detection
        private bool isMBBRunning = false;
        private DateTime lastMBBCheck = DateTime.MinValue;
        private readonly TimeSpan MBBCheckInterval = TimeSpan.FromSeconds(3);

        // ImGui UI
        private WindowSystem windowSystem;
        private MBBConfigWindow configWindow;

        public DalamudMBBBridge()
        {
            try
            {
                // Initialize Window System
                windowSystem = new WindowSystem("MBBBridge");
                configWindow = new MBBConfigWindow(this);
                windowSystem.AddWindow(configWindow);

                PluginInterface.UiBuilder.Draw += windowSystem.Draw;
                PluginInterface.UiBuilder.OpenConfigUi += OpenConfigUi;

                // Register command
                CommandManager.AddHandler(CommandName, new CommandInfo(OnCommand)
                {
                    HelpMessage = "Show MBB Bridge status and controls"
                });

                // FIXED: Focused approach to eliminate handler conflicts
                ChatGui.ChatMessage += OnChatMessage; // For non-Talk chat types only
                AddonLifecycle.RegisterListener(AddonEvent.PreRefresh, "Talk", OnTalkAddonPreReceive); // Single Talk handler

                // Also register for BattleTalk
                AddonLifecycle.RegisterListener(AddonEvent.PreSetup, "_BattleTalk", OnBattleTalkAddon);
                AddonLifecycle.RegisterListener(AddonEvent.PostSetup, "_BattleTalk", OnBattleTalkAddon);

                // CUTSCENE DIAGNOSTIC MODE - Discover actual addon names
                // Register universal diagnostic for cutscene discovery
                AddonLifecycle.RegisterListener(AddonEvent.PreSetup, OnCutsceneDiagnostic);
                AddonLifecycle.RegisterListener(AddonEvent.PostSetup, OnCutsceneDiagnostic);
                AddonLifecycle.RegisterListener(AddonEvent.PreRefresh, OnCutsceneDiagnostic);


                // 🎯 ECHOGLOSSIAN-BASED: Primary cutscene addon (confirmed working)
                AddonLifecycle.RegisterListener(AddonEvent.PreSetup, "TalkSubtitle", OnTalkSubtitleAddon);
                AddonLifecycle.RegisterListener(AddonEvent.PreRefresh, "TalkSubtitle", OnTalkSubtitleAddon);

                // 🎯 Choice Dialog Detection - Based on Research (PostSetup = most reliable)
                AddonLifecycle.RegisterListener(AddonEvent.PostSetup, "SelectString", OnSelectStringAddon);
                AddonLifecycle.RegisterListener(AddonEvent.PreRefresh, "SelectString", OnSelectStringAddon);

                // 🎯 Register for SelectIconString as backup
                AddonLifecycle.RegisterListener(AddonEvent.PostSetup, "SelectIconString", OnSelectIconStringAddon);
                AddonLifecycle.RegisterListener(AddonEvent.PreRefresh, "SelectIconString", OnSelectIconStringAddon);


                // Test multiple potential cutscene addon names based on research
                var potentialCutsceneAddons = new[] {
                    "Cutscene", "_Cutscene", "CutScene", "_CutScene",
                    "Movie", "_Movie", "MovieSubtitle", "_MovieSubtitle",
                    "Subtitle", "_Subtitle", "SubtitleDialog", "_SubtitleDialog",
                    "CutSceneSelectString", "_CutSceneSelectString"
                };

                foreach (var addonName in potentialCutsceneAddons)
                {
                    AddonLifecycle.RegisterListener(AddonEvent.PreSetup, addonName, OnCutsceneAddonTest);
                    AddonLifecycle.RegisterListener(AddonEvent.PostSetup, addonName, OnCutsceneAddonTest);
                    AddonLifecycle.RegisterListener(AddonEvent.PreRefresh, addonName, OnCutsceneAddonTest);
                    AddonLifecycle.RegisterListener(AddonEvent.PostRefresh, addonName, OnCutsceneAddonTest);
                }


                // Start named pipe server
                Task.Run(StartPipeServer);

                Log.Info("MBB Dalamud Bridge v1.4.10.4 initialized - Fixed icon display with images folder structure");
            }
            catch (Exception ex)
            {
                Log.Error($"Failed to initialize MBB Bridge: {ex.Message}");
            }
        }

        // ENHANCED DUPLICATE PREVENTION: Global message deduplication system
        private bool IsUniqueMessage(string speaker, string message, string type)
        {
            if (string.IsNullOrEmpty(message)) return false;

            var messageKey = $"{type}:{speaker}:{message}";
            var currentTime = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

            // Enhanced debug logging
            Log.Info($"[DUPLICATE CHECK] Key: {messageKey.Substring(0, Math.Min(80, messageKey.Length))}...");

            // Check if we've seen this exact message recently (within 3 seconds)
            if (globalMessageHistory.TryGetValue(messageKey, out var lastSeenTime))
            {
                var timeDiff = currentTime - lastSeenTime;
                Log.Info($"[DUPLICATE CHECK] Found existing entry, time diff: {timeDiff}s");
                if (timeDiff <= 3)
                {
                    Log.Info($"[DUPLICATE PREVENTION] ❌ BLOCKED duplicate {type}: {speaker}: {message.Substring(0, Math.Min(30, message.Length))}...");
                    return false; // Duplicate - block it
                }
            }

            // Record this message as seen
            globalMessageHistory[messageKey] = currentTime;
            Log.Info($"[DUPLICATE CHECK] ✅ ALLOWED new message {type}: {speaker}: {message.Substring(0, Math.Min(30, message.Length))}...");

            // Clean old entries periodically (every 100 messages)
            if (globalMessageHistory.Count > 100)
            {
                CleanOldMessageHistory(currentTime);
            }

            return true; // Unique message
        }

        private void CleanOldMessageHistory(long currentTime)
        {
            var keysToRemove = new List<string>();
            foreach (var kvp in globalMessageHistory)
            {
                if (currentTime - kvp.Value > 30) // Remove entries older than 30 seconds
                {
                    keysToRemove.Add(kvp.Key);
                }
            }

            foreach (var key in keysToRemove)
            {
                globalMessageHistory.TryRemove(key, out _);
            }

            Log.Debug($"[CLEANUP] Cleaned {keysToRemove.Count} old message entries. Active: {globalMessageHistory.Count}");
        }


        // DOCUMENTED WORKING METHOD: PreReceiveEvent with AtkValues (per guide)
        private unsafe void OnTalkAddonPreReceive(AddonEvent type, AddonArgs args)
        {
            try
            {
                // CRITICAL: Add debugging to see what events have AtkValues
                Log.Debug($"[TALK-{type}] Event received, Args type: {args.GetType().Name}");

                if (args is not AddonRefreshArgs refreshArgs)
                {
                    Log.Debug($"[TALK-{type}] Not AddonRefreshArgs, skipping");
                    return;
                }

                var updateAtkValues = (AtkValue*)refreshArgs.AtkValues;
                if (updateAtkValues == null)
                {
                    Log.Debug($"[TALK-{type}] AtkValues is null, skipping");
                    return;
                }

                Log.Debug($"[TALK-{type}] AtkValues found, processing...");

                // Extract text from AtkValues exactly as documented in guide
                // Speaker Node: updateAtkValues[1].String
                // Message Node: updateAtkValues[0].String
                string speakerName = updateAtkValues[1].String != null ?
                    MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[1].String.Value) : "";
                string message = MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[0].String.Value);

                // Use global duplicate prevention system
                if (IsUniqueMessage(speakerName, message, "dialogue"))
                {
                    var currentTime = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                    lastTalkMessage = message;
                    lastSpeaker = speakerName;

                    var textData = new TextHookData
                    {
                        Type = "dialogue",
                        Speaker = speakerName,
                        Message = message,
                        Timestamp = currentTime,
                        ChatType = 0x003D
                    };

                    messageQueue.Enqueue(textData);
                    Log.Info($"[TALK-{type}] Dialog captured: {speakerName}: {message.Substring(0, Math.Min(50, message.Length))}...");
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnTalkAddonPreReceive: {ex.Message}");
            }
        }

        private void OnChatMessage(XivChatType type, int timestamp, ref SeString sender, ref SeString message, ref bool isHandled)
        {
            try
            {
                // FIXED: Handle non-Talk chat types only to prevent overlap with AddonLifecycle
                // Exclude type 0x003D (Talk) as it's handled by OnTalkAddonPreReceive
                // 🔥 CRITICAL FIX: Block combat/duty spam ChatTypes with REAL values from logs
                var blockedTypes = new HashSet<int> {
                    0x0048, // System notifications

                    // Real ChatTypes from actual game logs
                    2092,   // Player actions (You use a bowl of mesquite soup)
                    2857,   // Combat damage (You hit Necron for X damage)
                    12457,  // Enemy damage (Necron hits you for X damage)
                    4139,   // Ability casting (Krile begins casting, uses abilities)
                    4777,   // Damage taken (Necron takes X damage)
                    2729,   // Critical hits (Critical! You hit X for Y damage)
                    4398,   // Status gained (gains the effect of)
                    4400,   // Status lost (loses the effect of)
                    4269,   // HP recovery (You recover X HP)

                    // v1.4.8.1 ADDITIONS: Equipment and System Messages
                    // 71 REMOVED - CONTAINS CUTSCENE TEXT! ("Or was it a gift─the terminal's parting miracle?")
                    2105,   // Equipment unequip messages (Ceremonial bangle of aiming unequipped) - RE-ADDED AFTER VERIFICATION

                    // v1.4.8.4 ADDITIONS: Combat Text Filtering (from live testing)
                    2221,   // HP absorption messages (You absorb X HP)
                    2735,   // Status effect messages (suffers the effect of)
                    10283,  // Spell casting/interruption messages (begins casting, is interrupted)
                    2874,   // Combat victory messages (You defeat X)

                    // v1.4.8.5 ADDITIONS: Job/Gear Change Messages
                    57,     // Gear/job change messages (Gear recommended, Job registered)

                    // v1.4.8.6 ADDITIONS: NPC/Monster Casting Messages
                    12331,  // NPC/Monster spell casting (begins casting, casts)

                    // v1.4.8.7 ADDITIONS: Hunt/Party Messages
                    11,     // Hunt board notifications and party status messages

                    // v1.4.8.9 ADDITIONS: Combat Zone Filtering (from live testing)
                    9001,   // Combat damage messages (The striking dummy takes X damage, Critical!)
                    10929,  // Status recovery messages (recovers from the effect of)
                    29,     // Other player actions/emotes (gives enthusiastic Lali-ho!)

                    // v1.4.10.1 ADDITIONS: Additional Combat Zone Filtering
                    9002,   // Combat immunity messages (The striking dummy is unaffected)
                    9007,   // Status effect application (suffers the effect of)
                    13105,  // Status effect recovery (recovers from the effect of)

                    // Legacy types (keep for safety)
                    2091, 2110, 2218, 2219, 2220, 2222, 2224, 2233, 2235, 2240, 2241, 2242,
                    2265, 2266, 2267, 2283, 2284, 2285, 2317, 2318, 2730, 2731, 3001,
                    8235, 8745, 8746, 8747, 8748, 8749, 8750, 8752, 8754,
                    10409, 10410, 10411, 10412, 10413
                };

                // 🔍 DEBUG: ChatType filtering
                Log.Info($"[DEBUG-FILTER] ChatType {(int)type} - Blocked: {blockedTypes.Contains((int)type)}");

                if (type != (XivChatType)0x003D && !blockedTypes.Contains((int)type))
                {
                    var speakerName = sender.TextValue;
                    var messageText = message.TextValue;

                    // Use global duplicate prevention system
                    if (IsUniqueMessage(speakerName, messageText, "chat"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "chat",
                            Speaker = speakerName,
                            Message = messageText,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = (int)type
                        };

                        messageQueue.Enqueue(textData);
                        Log.Info($"[CHAT] Non-Talk captured: {speakerName}: {messageText.Substring(0, Math.Min(50, messageText.Length))}... (ChatType: {(int)type})");
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnChatMessage: {ex.Message}");
            }
        }


        private unsafe void OnBattleTalkAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                var addon = GameGui.GetAddonByName("_BattleTalk", 1);
                if (addon.Address == IntPtr.Zero) return;

                var battleTalkAddon = (AtkUnitBase*)addon.Address;
                if (battleTalkAddon == null || !battleTalkAddon->IsVisible) return;

                // Get speaker (node ID 4) and message (node ID 6)
                var speakerNode = battleTalkAddon->GetNodeById(4);
                var messageNode = battleTalkAddon->GetNodeById(6);

                if (speakerNode != null && messageNode != null)
                {
                    var speakerTextNode = speakerNode->GetAsAtkTextNode();
                    var messageTextNode = messageNode->GetAsAtkTextNode();

                    if (speakerTextNode != null && messageTextNode != null)
                    {
                        var speaker = MemoryHelper.ReadSeStringAsString(out _, (nint)speakerTextNode->NodeText.StringPtr.Value);
                        var message = MemoryHelper.ReadSeStringAsString(out _, (nint)messageTextNode->NodeText.StringPtr.Value);

                        // Use global duplicate prevention system
                        if (IsUniqueMessage(speaker, message, "battle"))
                        {
                            var textData = new TextHookData
                            {
                                Type = "battle",
                                Speaker = speaker,
                                Message = message,
                                Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                ChatType = 0x0044 // BattleTalk type
                            };

                            messageQueue.Enqueue(textData);
                            Log.Info($"[BATTLETALK] Captured: {speaker}: {message.Substring(0, Math.Min(50, message.Length))}...");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnBattleTalkAddon: {ex.Message}");
            }
        }

        // CUTSCENE DIAGNOSTIC: Universal listener to discover addon names
        private unsafe void OnCutsceneDiagnostic(AddonEvent type, AddonArgs args)
        {
            try
            {
                var addonName = args.AddonName;

                // Filter for potential cutscene-related addons
                if (addonName != null && (
                    addonName.Contains("Cut", StringComparison.OrdinalIgnoreCase) ||
                    addonName.Contains("Scene", StringComparison.OrdinalIgnoreCase) ||
                    addonName.Contains("Movie", StringComparison.OrdinalIgnoreCase) ||
                    addonName.Contains("Subtitle", StringComparison.OrdinalIgnoreCase) ||
                    addonName.Contains("Dialog", StringComparison.OrdinalIgnoreCase) ||
                    addonName.Contains("Text", StringComparison.OrdinalIgnoreCase)))
                {
                    Log.Info($"🔍 [CUTSCENE DISCOVERY] Potential addon found: '{addonName}' - Event: {type}");

                    // Try to extract text from this addon
                    var addon = GameGui.GetAddonByName(addonName, 1);
                    if (addon.Address != IntPtr.Zero)
                    {
                        var atkAddon = (AtkUnitBase*)addon.Address;
                        if (atkAddon != null && atkAddon->IsVisible)
                        {
                            Log.Info($"✅ [CUTSCENE DISCOVERY] '{addonName}' is ACTIVE and VISIBLE!");

                            // Attempt text extraction from various nodes
                            for (uint nodeId = 0; nodeId <= 10; nodeId++)
                            {
                                var node = atkAddon->GetNodeById(nodeId);
                                if (node != null)
                                {
                                    var textNode = node->GetAsAtkTextNode();
                                    if (textNode != null && textNode->NodeText.StringPtr != null)
                                    {
                                        var text = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode->NodeText.StringPtr.Value);
                                        if (!string.IsNullOrEmpty(text) && text.Length > 3)
                                        {
                                            Log.Info($"📝 [CUTSCENE TEXT FOUND] Addon: '{addonName}', Node {nodeId}: {text.Substring(0, Math.Min(100, text.Length))}...");
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                // Silent fail for diagnostic
            }
        }


        // Test handler for specific cutscene addon names
        private unsafe void OnCutsceneAddonTest(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Info($"🎬 [CUTSCENE TEST] Addon '{args.AddonName}' triggered! Event: {type}");

                var addon = GameGui.GetAddonByName(args.AddonName, 1);
                if (addon.Address == IntPtr.Zero) return;

                var cutsceneAddon = (AtkUnitBase*)addon.Address;
                if (cutsceneAddon == null || !cutsceneAddon->IsVisible) return;

                Log.Info($"🎬 [CUTSCENE ACTIVE] '{args.AddonName}' is visible and ready for text extraction!");

                // Try different extraction methods
                ExtractCutsceneTextMethod1(args, cutsceneAddon);
                ExtractCutsceneTextMethod2(cutsceneAddon);
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnCutsceneAddonTest: {ex.Message}");
            }
        }

        private unsafe void ExtractCutsceneTextMethod1(AddonArgs args, AtkUnitBase* addon)
        {
            // Method 1: Try AtkValues if available
            if (args is AddonRefreshArgs refreshArgs && refreshArgs.AtkValues != null)
            {
                var updateAtkValues = (AtkValue*)refreshArgs.AtkValues;
                if (updateAtkValues != null)
                {
                    for (int i = 0; i < 5; i++)
                    {
                        if (updateAtkValues[i].String != null)
                        {
                            var text = MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[i].String.Value);
                            if (!string.IsNullOrEmpty(text) && text.Length > 3)
                            {
                                Log.Info($"📝 [METHOD1] AtkValue[{i}]: {text.Substring(0, Math.Min(100, text.Length))}...");

                                // Queue the message if unique
                                if (IsUniqueMessage("", text, "cutscene"))
                                {
                                    var textData = new TextHookData
                                    {
                                        Type = "cutscene",
                                        Speaker = "",
                                        Message = text,
                                        Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                        ChatType = 0x0045
                                    };
                                    messageQueue.Enqueue(textData);
                                    Log.Info($"✅ [CUTSCENE CAPTURED] {text.Substring(0, Math.Min(50, text.Length))}...");
                                }
                            }
                        }
                    }
                }
            }
        }

        private unsafe void ExtractCutsceneTextMethod2(AtkUnitBase* addon)
        {
            // Method 2: Comprehensive node scanning
            for (uint nodeId = 0; nodeId <= 20; nodeId++)
            {
                var node = addon->GetNodeById(nodeId);
                if (node != null)
                {
                    var textNode = node->GetAsAtkTextNode();
                    if (textNode != null && textNode->NodeText.StringPtr != null)
                    {
                        var text = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode->NodeText.StringPtr.Value);
                        if (!string.IsNullOrEmpty(text) && text.Length > 5)
                        {
                            Log.Info($"📝 [METHOD2] Node {nodeId}: {text.Substring(0, Math.Min(100, text.Length))}...");

                            // Queue if unique and looks like dialogue
                            if (IsUniqueMessage("", text, "cutscene") && !text.StartsWith("SE.") && !text.Contains("\\n"))
                            {
                                var textData = new TextHookData
                                {
                                    Type = "cutscene",
                                    Speaker = "",
                                    Message = text,
                                    Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                    ChatType = 0x0045
                                };
                                messageQueue.Enqueue(textData);
                                Log.Info($"✅ [CUTSCENE CAPTURED] {text.Substring(0, Math.Min(50, text.Length))}...");
                            }
                        }
                    }
                }
            }
        }

        // LEGACY: Keep old handler as fallback (will be removed after testing)
        private unsafe void OnCutsceneAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Debug($"[CUTSCENE-{type}] SubtitleDialog event received");

                // Use verified addon name only
                var addon = GameGui.GetAddonByName("SubtitleDialog", 1);
                if (addon.Address == IntPtr.Zero) return;

                var cutsceneAddon = (AtkUnitBase*)addon.Address;
                if (cutsceneAddon == null || !cutsceneAddon->IsVisible) return;

                Log.Debug($"[CUTSCENE] SubtitleDialog is active and visible");

                // Focus on PreRefresh/PostRefresh events for text content
                if (args is AddonRefreshArgs refreshArgs && refreshArgs.AtkValues != null)
                {
                    // Method 1: Try AtkValues extraction
                    var updateAtkValues = (AtkValue*)refreshArgs.AtkValues;
                    if (updateAtkValues != null)
                    {
                        string speakerName = updateAtkValues[1].String != null ?
                            MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[1].String.Value) : "";
                        string message = MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[0].String.Value);

                        // Use global duplicate prevention system
                        if (IsUniqueMessage(speakerName, message, "cutscene"))
                        {
                            var textData = new TextHookData
                            {
                                Type = "cutscene",
                                Speaker = speakerName,
                                Message = message,
                                Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                ChatType = 0x0045 // Custom cutscene type
                            };

                            messageQueue.Enqueue(textData);
                            Log.Info($"[CUTSCENE] Captured: {speakerName}: {message.Substring(0, Math.Min(50, message.Length))}...");
                            return;
                        }
                    }
                }

                // Method 2: Node-based extraction as fallback
                for (uint nodeId = 2; nodeId <= 6; nodeId++)
                {
                    var textNode = cutsceneAddon->GetNodeById(nodeId);
                    if (textNode != null)
                    {
                        var atkTextNode = textNode->GetAsAtkTextNode();
                        if (atkTextNode != null && atkTextNode->NodeText.StringPtr != null)
                        {
                            var text = MemoryHelper.ReadSeStringAsString(out _, (nint)atkTextNode->NodeText.StringPtr.Value);
                            if (!string.IsNullOrEmpty(text) && text.Length > 5 && IsUniqueMessage("", text, "cutscene"))
                            {
                                var textData = new TextHookData
                                {
                                    Type = "cutscene",
                                    Speaker = "",
                                    Message = text,
                                    Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                    ChatType = 0x0045
                                };

                                messageQueue.Enqueue(textData);
                                Log.Info($"[CUTSCENE] Node {nodeId}: {text.Substring(0, Math.Min(50, text.Length))}...");
                                return;
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnCutsceneAddon: {ex.Message}");
            }
        }

        // 🎯 ECHOGLOSSIAN-BASED: TalkSubtitle Handler (Primary Cutscene)
        private unsafe void OnTalkSubtitleAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Debug($"[TALKSUBTITLE-{type}] Event received - Primary cutscene handler");

                var addon = GameGui.GetAddonByName("TalkSubtitle", 1);
                if (addon.Address == IntPtr.Zero) return;

                var talkSubtitleAddon = (AtkUnitBase*)addon.Address;
                if (talkSubtitleAddon == null || !talkSubtitleAddon->IsVisible) return;

                Log.Debug($"[TALKSUBTITLE] Addon is active and visible");

                // Method 1: AtkValues approach (Echoglossian method)
                if (args is AddonSetupArgs setupArgs && setupArgs.AtkValues != null)
                {
                    var setupAtkValues = (AtkValue*)setupArgs.AtkValues;
                    if (setupAtkValues != null && setupAtkValues[0].String != null)
                    {
                        var textToTranslate = MemoryHelper.ReadSeStringAsString(out _, (nint)setupAtkValues[0].String.Value);

                        if (!string.IsNullOrEmpty(textToTranslate) && textToTranslate.Length > 3)
                        {
                            Log.Info($"[TALKSUBTITLE] AtkValue text: {textToTranslate.Substring(0, Math.Min(100, textToTranslate.Length))}...");

                            if (IsUniqueMessage("", textToTranslate, "cutscene"))
                            {
                                var textData = new TextHookData
                                {
                                    Type = "cutscene",
                                    Speaker = "", // Cutscenes often don't have separate speaker
                                    Message = textToTranslate,
                                    Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                    ChatType = 0x0047 // Unique type for TalkSubtitle
                                };
                                messageQueue.Enqueue(textData);
                                Log.Info($"✅ [CUTSCENE-TALKSUBTITLE] Captured via AtkValues: {textToTranslate.Substring(0, Math.Min(50, textToTranslate.Length))}...");
                                return;
                            }
                        }
                    }
                }

                // Method 2: Multi-node text extraction (Echoglossian approach - nodes 2,3,4)
                var textNode2 = talkSubtitleAddon->GetTextNodeById(2);
                var textNode3 = talkSubtitleAddon->GetTextNodeById(3);
                var textNode4 = talkSubtitleAddon->GetTextNodeById(4);

                // Try node 2 first (primary)
                if (textNode2 != null && !textNode2->NodeText.IsEmpty)
                {
                    var text = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode2->NodeText.StringPtr.Value);
                    if (!string.IsNullOrEmpty(text) && text.Length > 3 && IsUniqueMessage("", text, "cutscene"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "cutscene",
                            Speaker = "",
                            Message = text,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0047
                        };
                        messageQueue.Enqueue(textData);
                        Log.Info($"✅ [CUTSCENE-TALKSUBTITLE] Captured via Node2: {text.Substring(0, Math.Min(50, text.Length))}...");
                        return;
                    }
                }

                // Try node 3 as backup
                if (textNode3 != null && !textNode3->NodeText.IsEmpty)
                {
                    var text = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode3->NodeText.StringPtr.Value);
                    if (!string.IsNullOrEmpty(text) && text.Length > 3 && IsUniqueMessage("", text, "cutscene"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "cutscene",
                            Speaker = "",
                            Message = text,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0047
                        };
                        messageQueue.Enqueue(textData);
                        Log.Info($"✅ [CUTSCENE-TALKSUBTITLE] Captured via Node3: {text.Substring(0, Math.Min(50, text.Length))}...");
                        return;
                    }
                }

                // Try node 4 as final backup
                if (textNode4 != null && !textNode4->NodeText.IsEmpty)
                {
                    var text = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode4->NodeText.StringPtr.Value);
                    if (!string.IsNullOrEmpty(text) && text.Length > 3 && IsUniqueMessage("", text, "cutscene"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "cutscene",
                            Speaker = "",
                            Message = text,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0047
                        };
                        messageQueue.Enqueue(textData);
                        Log.Info($"✅ [CUTSCENE-TALKSUBTITLE] Captured via Node4: {text.Substring(0, Math.Min(50, text.Length))}...");
                        return;
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnTalkSubtitleAddon: {ex.Message}");
            }
        }

        // 🎯 Choice Dialog Handler - Based on Research (Node 2, 15-19)
        private unsafe void OnSelectStringAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Info($"[CHOICE-DIALOG] SelectString {type} event detected!");

                var addon = GameGui.GetAddonByName("SelectString", 1);
                if (addon.Address == IntPtr.Zero)
                {
                    Log.Info($"[CHOICE-DEBUG] SelectString addon address is null");
                    return;
                }

                var atkAddon = (AtkUnitBase*)addon.Address;
                if (atkAddon == null || !atkAddon->IsVisible)
                {
                    Log.Info($"[CHOICE-DEBUG] SelectString addon not visible or null");
                    return;
                }

                // Enhanced validation from research
                if (atkAddon->UldManager.LoadedState != AtkLoadState.Loaded)
                {
                    Log.Info($"[CHOICE-DEBUG] SelectString not fully loaded");
                    return;
                }

                Log.Info($"[CHOICE-DEBUG] SelectString has {atkAddon->UldManager.NodeListCount} nodes");

                // Extract dialog title (Node 2 - "What will you say?")
                string dialogTitle = "";
                var titleNode = atkAddon->GetNodeById(2);
                if (titleNode != null && titleNode->Type == NodeType.Text)
                {
                    var textNode = (AtkTextNode*)titleNode;
                    if (textNode->NodeText.StringPtr != null)
                    {
                        dialogTitle = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode->NodeText.StringPtr.Value);
                        if (!string.IsNullOrEmpty(dialogTitle))
                        {
                            Log.Info($"[CHOICE-TITLE] Node 2: {dialogTitle}");
                        }
                    }
                }

                // Extract choice options (Nodes 15-19)
                var choices = new List<string>();
                uint[] choiceNodeIds = { 15, 16, 17, 18, 19 };

                foreach (var nodeId in choiceNodeIds)
                {
                    var node = atkAddon->GetNodeById(nodeId);
                    if (node == null || node->Type != NodeType.Text) continue;

                    var textNode = (AtkTextNode*)node;
                    if (!textNode->AtkResNode.IsVisible()) continue;

                    if (textNode->NodeText.StringPtr != null)
                    {
                        var choiceText = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode->NodeText.StringPtr.Value);
                        if (!string.IsNullOrEmpty(choiceText))
                        {
                            choices.Add(choiceText);
                            Log.Info($"[CHOICE-OPTION] Node {nodeId}: {choiceText}");
                        }
                    }
                }

                // Send choice data if we have both title and choices
                if (!string.IsNullOrEmpty(dialogTitle) && choices.Count > 0)
                {
                    // Use global duplicate prevention system
                    var combinedText = $"{dialogTitle} | {string.Join(" | ", choices)}";
                    if (IsUniqueMessage("Choice", combinedText, "choice"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "choice",
                            Speaker = "",
                            Message = combinedText,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0046 // Choice dialog ChatType
                        };

                        messageQueue.Enqueue(textData);
                        Log.Info($"[CHOICE-SUCCESS] Sent: {dialogTitle} with {choices.Count} options");
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"[CHOICE-ERROR] {ex.Message}");
            }
        }

        // 🎯 SelectIconString Handler - Based on Research (Similar to SelectString)
        private unsafe void OnSelectIconStringAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Info($"[CHOICE-DIALOG] SelectIconString {type} event detected!");

                var addon = GameGui.GetAddonByName("SelectIconString", 1);
                if (addon.Address == IntPtr.Zero)
                {
                    Log.Info($"[CHOICE-DEBUG] SelectIconString addon address is null");
                    return;
                }

                var atkAddon = (AtkUnitBase*)addon.Address;
                if (atkAddon == null || !atkAddon->IsVisible)
                {
                    Log.Info($"[CHOICE-DEBUG] SelectIconString addon not visible or null");
                    return;
                }

                // Enhanced validation from research
                if (atkAddon->UldManager.LoadedState != AtkLoadState.Loaded)
                {
                    Log.Info($"[CHOICE-DEBUG] SelectIconString not fully loaded");
                    return;
                }

                Log.Info($"[CHOICE-DEBUG] SelectIconString has {atkAddon->UldManager.NodeListCount} nodes");

                // For SelectIconString, try broader node range due to icons
                var choices = new List<string>();
                for (uint nodeId = 3; nodeId <= 20; nodeId++)
                {
                    var node = atkAddon->GetNodeById(nodeId);
                    if (node == null || node->Type != NodeType.Text) continue;

                    var textNode = (AtkTextNode*)node;
                    if (!textNode->AtkResNode.IsVisible()) continue;

                    if (textNode->NodeText.StringPtr != null)
                    {
                        var choiceText = MemoryHelper.ReadSeStringAsString(out _, (nint)textNode->NodeText.StringPtr.Value);
                        if (!string.IsNullOrEmpty(choiceText) && choiceText.Length > 2)
                        {
                            choices.Add(choiceText);
                            Log.Info($"[CHOICE-ICON] Node {nodeId}: {choiceText}");
                        }
                    }
                }

                if (choices.Count > 0)
                {
                    var combinedChoices = string.Join(" | ", choices);
                    if (IsUniqueMessage("IconChoice", combinedChoices, "choice"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "choice",
                            Speaker = "Icon Choice",
                            Message = combinedChoices,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0047 // Custom icon choice type
                        };

                        messageQueue.Enqueue(textData);
                        Log.Info($"[CHOICE-ICON-SUCCESS] Sent: {choices.Count} icon choices");
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"[CHOICE-ERROR] SelectIconString: {ex.Message}");
            }
        }

        // 🎯 OLD: Choice Dialog Handler (backup)
        private unsafe void OnChoiceAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                string addonName = args.AddonName ?? "Choice";
                Log.Info($"[CHOICE-{type}] Event received - {addonName}");

                // ✅ PROVEN PATTERN: Same as Talk (100% success)
                // Method 1: Try AtkValues extraction (primary method)
                if (args is AddonRefreshArgs refreshArgs && refreshArgs.AtkValues != null)
                {
                    var updateAtkValues = (AtkValue*)refreshArgs.AtkValues;
                    if (updateAtkValues != null)
                    {
                        // Try to extract choice text from AtkValues
                        string choiceText = "";
                        try
                        {
                            // Try multiple AtkValue indices (like Talk does)
                            for (int i = 0; i < 10; i++)
                            {
                                if (updateAtkValues[i].Type == FFXIVClientStructs.FFXIV.Component.GUI.ValueType.String && updateAtkValues[i].String != null)
                                {
                                    var text = MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[i].String.Value);
                                    if (!string.IsNullOrEmpty(text) && text.Length > 3)
                                    {
                                        choiceText = text;
                                        Log.Info($"[CHOICE-ATKVALUES] Found at index {i}: {text.Substring(0, Math.Min(50, text.Length))}...");
                                        break;
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Log.Error($"[CHOICE-ATKVALUES] Error: {ex.Message}");
                        }

                        // Send choice text if found
                        if (!string.IsNullOrEmpty(choiceText) && IsUniqueMessage("", choiceText, "choice"))
                        {
                            var textData = new TextHookData
                            {
                                Type = "choice",
                                Speaker = "",
                                Message = choiceText,
                                Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                ChatType = 0x0046
                            };
                            messageQueue.Enqueue(textData);
                            Log.Info($"✅ [CHOICE-SUCCESS] {addonName}: {choiceText.Substring(0, Math.Min(50, choiceText.Length))}...");
                            return; // Success, exit early
                        }
                    }
                }

                // Method 2: Fallback node-based extraction (like Talk fallback)
                var addon = GameGui.GetAddonByName(addonName, 1);
                if (addon.Address != IntPtr.Zero)
                {
                    var atkAddon = (AtkUnitBase*)addon.Address;
                    if (atkAddon != null && atkAddon->IsVisible)
                    {
                        // Try known choice dialog nodes
                        var nodeIds = new uint[] { 2, 3, 4, 5, 6, 7 };
                        foreach (var nodeId in nodeIds)
                        {
                            var textNode = atkAddon->GetNodeById(nodeId);
                            if (textNode != null)
                            {
                                var atkTextNode = textNode->GetAsAtkTextNode();
                                if (atkTextNode != null && !atkTextNode->NodeText.IsEmpty)
                                {
                                    try
                                    {
                                        var text = MemoryHelper.ReadSeStringAsString(out _, (nint)atkTextNode->NodeText.StringPtr.Value);
                                        if (!string.IsNullOrEmpty(text) && text.Length > 3 && IsUniqueMessage("", text, "choice"))
                                        {
                                            var textData = new TextHookData
                                            {
                                                Type = "choice",
                                                Speaker = "",
                                                Message = text,
                                                Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                                ChatType = 0x0046
                                            };
                                            messageQueue.Enqueue(textData);
                                            Log.Info($"✅ [CHOICE-NODE{nodeId}] {addonName}: {text.Substring(0, Math.Min(50, text.Length))}...");
                                        }
                                    }
                                    catch (Exception ex)
                                    {
                                        Log.Error($"[CHOICE-NODE{nodeId}] Error: {ex.Message}");
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnChoiceAddon: {ex.Message}");
            }
        }

        // 🎯 OLD: Choice Dialog Handler (backup)
        private unsafe void OnChoiceAddonOld(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Info($"[CHOICE-{type}] Event received");

                var addon = GameGui.GetAddonByName("SelectString", 1);
                if (addon.Address == IntPtr.Zero) return;

                var selectAddon = (AtkUnitBase*)addon.Address;
                if (selectAddon == null || !selectAddon->IsVisible) return;

                // SelectString typically has:
                // - Text prompt (what the NPC is asking)
                // - Multiple choice options
                // Research shows nodes 2-15 often contain choice text

                // Method 1: Try AtkValues if available
                if (args is AddonRefreshArgs refreshArgs && refreshArgs.AtkValues != null)
                {
                    var updateAtkValues = (AtkValue*)refreshArgs.AtkValues;
                    if (updateAtkValues != null)
                    {
                        // Try to get prompt text (usually index 0)
                        string promptText = updateAtkValues[0].String != null ?
                            MemoryHelper.ReadSeStringAsString(out _, (nint)updateAtkValues[0].String.Value) : "";

                        // Use global duplicate prevention system
                        if (IsUniqueMessage("System", promptText, "choice"))
                        {
                            var textData = new TextHookData
                            {
                                Type = "choice",
                                Speaker = "System", // Choice dialogs usually don't have speaker
                                Message = promptText,
                                Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                ChatType = 0x0046 // Custom choice type
                            };

                            messageQueue.Enqueue(textData);
                            Log.Info($"[CHOICE] Prompt captured: {promptText.Substring(0, Math.Min(50, promptText.Length))}...");
                            return;
                        }
                    }
                }

                // Method 2: Extract choice options from nodes
                var choiceTexts = new List<string>();
                for (uint nodeId = 2; nodeId <= 15; nodeId++)
                {
                    var textNode = selectAddon->GetNodeById(nodeId);
                    if (textNode != null)
                    {
                        var atkTextNode = textNode->GetAsAtkTextNode();
                        if (atkTextNode != null && atkTextNode->NodeText.StringPtr != null)
                        {
                            var text = MemoryHelper.ReadSeStringAsString(out _, (nint)atkTextNode->NodeText.StringPtr.Value);
                            if (!string.IsNullOrEmpty(text) && text.Length > 2)
                            {
                                choiceTexts.Add(text);
                            }
                        }
                    }
                }

                // Send all choices as a combined message with duplicate prevention
                if (choiceTexts.Count > 0)
                {
                    var combinedChoices = string.Join(" | ", choiceTexts);
                    // Use global duplicate prevention system
                    if (IsUniqueMessage("Choices", combinedChoices, "choice"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "choice",
                            Speaker = "Choices",
                            Message = combinedChoices,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0046
                        };

                        messageQueue.Enqueue(textData);
                        Log.Info($"[CHOICE] {choiceTexts.Count} options: {combinedChoices.Substring(0, Math.Min(100, combinedChoices.Length))}...");
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnChoiceAddon: {ex.Message}");
            }
        }

        // 🎯 NEW: Icon Choice Dialog Handler (SelectIconString)
        private unsafe void OnIconChoiceAddon(AddonEvent type, AddonArgs args)
        {
            try
            {
                Log.Debug($"[ICONCHOICE-{type}] Event received");

                var addon = GameGui.GetAddonByName("SelectIconString", 1);
                if (addon.Address == IntPtr.Zero) return;

                var selectAddon = (AtkUnitBase*)addon.Address;
                if (selectAddon == null || !selectAddon->IsVisible) return;

                // Similar to SelectString but with icons
                // Extract text from nodes (usually higher node IDs for icon choices)
                var choiceTexts = new List<string>();
                for (uint nodeId = 3; nodeId <= 20; nodeId++) // Icon choices might use different range
                {
                    var textNode = selectAddon->GetNodeById(nodeId);
                    if (textNode != null)
                    {
                        var atkTextNode = textNode->GetAsAtkTextNode();
                        if (atkTextNode != null && atkTextNode->NodeText.StringPtr != null)
                        {
                            var text = MemoryHelper.ReadSeStringAsString(out _, (nint)atkTextNode->NodeText.StringPtr.Value);
                            if (!string.IsNullOrEmpty(text) && text.Length > 2)
                            {
                                choiceTexts.Add(text);
                            }
                        }
                    }
                }

                if (choiceTexts.Count > 0)
                {
                    var combinedChoices = string.Join(" | ", choiceTexts);
                    // Use global duplicate prevention system
                    if (IsUniqueMessage("Icon Choices", combinedChoices, "choice"))
                    {
                        var textData = new TextHookData
                        {
                            Type = "choice",
                            Speaker = "Icon Choices",
                            Message = combinedChoices,
                            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                            ChatType = 0x0047 // Custom icon choice type
                        };

                        messageQueue.Enqueue(textData);
                        Log.Info($"[ICONCHOICE] {choiceTexts.Count} options: {combinedChoices.Substring(0, Math.Min(100, combinedChoices.Length))}...");
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in OnIconChoiceAddon: {ex.Message}");
            }
        }

        private void OpenConfigUi()
        {
            configWindow.IsOpen = true;
        }

        private void OnCommand(string command, string args)
        {
            args = args.Trim().ToLower();

            switch (args)
            {
                case "launch":
                    LaunchMBB();
                    break;
                case "status":
                    ShowStatus();
                    break;
                case "help":
                    ShowHelp();
                    break;
                default:
                    configWindow.IsOpen = true;
                    break;
            }
        }

        private void ShowStatus()
        {
            var mbbRunning = CheckMBBProcess();
            var connectionStatus = isConnected ? "🟢 Connected" : "🟡 Waiting";
            var mbbStatus = mbbRunning ? "🟢 Running" : "🔴 Not Running";

            ChatGui.Print($"[MBB Bridge] Bridge: {connectionStatus} | MBB: {mbbStatus} | Queue: {messageQueue.Count}");

            if (!isConnected)
            {
                ChatGui.Print("[MBB Bridge] Waiting for MBB connection...");
                ChatGui.Print("[MBB Bridge] Make sure MBB is running with Dalamud Bridge Mode enabled");
            }
            else
            {
                ChatGui.Print("[MBB Bridge] Bridge is active with IMMEDIATE Talk dialog capture!");
            }
        }

        private void ShowHelp()
        {
            ChatGui.Print("🌉 MBB Dalamud Bridge Commands:");
            ChatGui.Print("/mbb - Show configuration panel");
            ChatGui.Print("/mbb status - Show quick status");
            ChatGui.Print("/mbb launch - Launch MBB application");
            ChatGui.Print("/mbb help - Show this help");
        }

        public bool CheckMBBProcess()
        {
            try
            {
                // Check only every few seconds to avoid performance impact
                if (DateTime.Now - lastMBBCheck < MBBCheckInterval)
                {
                    return isMBBRunning;
                }

                lastMBBCheck = DateTime.Now;

                var processes = Process.GetProcessesByName("python");
                foreach (var process in processes)
                {
                    try
                    {
                        var cmdLine = GetCommandLine(process);
                        if (cmdLine != null && cmdLine.Contains("MBB.py"))
                        {
                            isMBBRunning = true;
                            return true;
                        }
                    }
                    catch
                    {
                        // Ignore access denied errors
                    }
                }

                isMBBRunning = false;
                return false;
            }
            catch
            {
                isMBBRunning = false;
                return false;
            }
        }

        private static string? GetCommandLine(Process process)
        {
            try
            {
                using var searcher = new System.Management.ManagementObjectSearcher(
                    $"SELECT CommandLine FROM Win32_Process WHERE ProcessId = {process.Id}");
                using var objects = searcher.Get();
                foreach (System.Management.ManagementObject obj in objects)
                {
                    return obj["CommandLine"]?.ToString();
                }
            }
            catch
            {
                // Ignore errors
            }
            return null;
        }

        public void LaunchMBB()
        {
            try
            {
                var mbbPath = @"C:\Yariman_Babel\MbbDalamud_bridge\MBB.py";
                if (File.Exists(mbbPath))
                {
                    var startInfo = new ProcessStartInfo
                    {
                        FileName = "python",
                        Arguments = $"\"{mbbPath}\"",
                        WorkingDirectory = Path.GetDirectoryName(mbbPath),
                        UseShellExecute = false,
                        CreateNoWindow = false
                    };

                    Process.Start(startInfo);
                    ChatGui.Print("[MBB Bridge] Launching MBB application...");
                    Log.Info("[MBB Bridge] MBB launch initiated");
                }
                else
                {
                    ChatGui.PrintError("[MBB Bridge] MBB.py not found at expected location!");
                    Log.Error($"[MBB Bridge] MBB.py not found at: {mbbPath}");
                }
            }
            catch (Exception ex)
            {
                ChatGui.PrintError($"[MBB Bridge] Failed to launch MBB: {ex.Message}");
                Log.Error($"[MBB Bridge] Launch error: {ex.Message}");
            }
        }

        public bool IsConnected => isConnected;
        public bool IsMBBRunning => CheckMBBProcess();
        public int MessageQueueCount => messageQueue.Count;

        public void RefreshMBBStatus()
        {
            lastMBBCheck = DateTime.MinValue; // Force refresh
        }


        private async Task StartPipeServer()
        {
            while (isRunning)
            {
                try
                {
                    pipeServer = new NamedPipeServerStream(
                        "mbb_dalamud_bridge",
                        PipeDirection.Out,
                        1,
                        PipeTransmissionMode.Byte,
                        PipeOptions.Asynchronous);

                    Log.Info("Waiting for MBB connection...");
                    await pipeServer.WaitForConnectionAsync();

                    isConnected = true;
                    Log.Info("MBB connected!");

                    // Send queued messages
                    using var writer = new StreamWriter(pipeServer, Encoding.UTF8);
                    writer.AutoFlush = true;

                    while (isConnected && pipeServer.IsConnected)
                    {
                        if (messageQueue.TryDequeue(out var data))
                        {
                            var json = JsonSerializer.Serialize(data);
                            await writer.WriteLineAsync(json);
                            Log.Debug($"Sent to MBB: {json.Substring(0, Math.Min(100, json.Length))}...");
                        }
                        else
                        {
                            await Task.Delay(10);
                        }
                    }
                }
                catch (Exception ex)
                {
                    // Only log significant errors, not normal disconnections
                    if (ex.Message.Contains("Pipe is broken") || ex.Message.Contains("The pipe has been ended"))
                    {
                        Log.Debug($"Client disconnected: {ex.Message}");
                    }
                    else
                    {
                        Log.Error($"Pipe server error: {ex.Message}");
                    }
                }
                finally
                {
                    isConnected = false;
                    pipeServer?.Dispose();
                    pipeServer = null;
                }

                if (isRunning)
                {
                    Log.Debug("Restarting pipe server in 2 seconds...");
                    await Task.Delay(2000); // Faster reconnection
                }
            }
        }

        public void Dispose()
        {
            try
            {
                isRunning = false;
                isConnected = false;

                // Dispose UI resources
                PluginInterface.UiBuilder.Draw -= windowSystem.Draw;
                PluginInterface.UiBuilder.OpenConfigUi -= OpenConfigUi;

                windowSystem.RemoveAllWindows();
                configWindow?.Dispose();

                CommandManager.RemoveHandler(CommandName);

            // Unregister addon events - updated for fixed handlers
            ChatGui.ChatMessage -= OnChatMessage;
            AddonLifecycle.UnregisterListener(AddonEvent.PreRefresh, "Talk", OnTalkAddonPreReceive);
            AddonLifecycle.UnregisterListener(AddonEvent.PreSetup, "_BattleTalk", OnBattleTalkAddon);
            AddonLifecycle.UnregisterListener(AddonEvent.PostSetup, "_BattleTalk", OnBattleTalkAddon);

            // Unregister Choice Dialog events (updated for research-based implementation)
            AddonLifecycle.UnregisterListener(AddonEvent.PostSetup, "SelectString", OnSelectStringAddon);
            AddonLifecycle.UnregisterListener(AddonEvent.PreRefresh, "SelectString", OnSelectStringAddon);
            AddonLifecycle.UnregisterListener(AddonEvent.PostSetup, "SelectIconString", OnSelectIconStringAddon);
            AddonLifecycle.UnregisterListener(AddonEvent.PreRefresh, "SelectIconString", OnSelectIconStringAddon);

            // Unregister diagnostic listeners
            AddonLifecycle.UnregisterListener(AddonEvent.PreSetup, OnCutsceneDiagnostic);
            AddonLifecycle.UnregisterListener(AddonEvent.PostSetup, OnCutsceneDiagnostic);
            AddonLifecycle.UnregisterListener(AddonEvent.PreRefresh, OnCutsceneDiagnostic);

            // Unregister all potential cutscene addons
            var potentialCutsceneAddons = new[] {
                "Cutscene", "_Cutscene", "CutScene", "_CutScene",
                "Movie", "_Movie", "MovieSubtitle", "_MovieSubtitle",
                "Subtitle", "_Subtitle", "SubtitleDialog", "_SubtitleDialog",
                "CutSceneSelectString", "_CutSceneSelectString"
            };

            foreach (var addonName in potentialCutsceneAddons)
            {
                AddonLifecycle.UnregisterListener(AddonEvent.PreSetup, addonName, OnCutsceneAddonTest);
                AddonLifecycle.UnregisterListener(AddonEvent.PostSetup, addonName, OnCutsceneAddonTest);
                AddonLifecycle.UnregisterListener(AddonEvent.PreRefresh, addonName, OnCutsceneAddonTest);
                AddonLifecycle.UnregisterListener(AddonEvent.PostRefresh, addonName, OnCutsceneAddonTest);
            }

                pipeServer?.Dispose();

                Log.Info("[MBB Bridge] Plugin disposed successfully");
            }
            catch (Exception ex)
            {
                Log.Error($"[MBB Bridge] Dispose error: {ex.Message}");
            }
        }

        // 🔍 DIAGNOSTIC: Universal addon event listener for cutscene discovery
        private unsafe void OnUniversalAddonEvent(AddonEvent type, AddonArgs args)
        {
            try
            {
                var addonName = args.AddonName;

                // Only log potential cutscene/movie/dialogue related addons
                if (addonName != null && (
                    addonName.Contains("Cut") ||
                    addonName.Contains("Scene") ||
                    addonName.Contains("Movie") ||
                    addonName.Contains("Dialog") ||
                    addonName.Contains("Subtitle") ||
                    addonName.Contains("Text") ||
                    addonName.Contains("Narration") ||
                    addonName.Equals("Cutscene", StringComparison.OrdinalIgnoreCase) ||
                    addonName.Equals("Movie", StringComparison.OrdinalIgnoreCase)))
                {
                    Log.Info($"🔍 [DIAGNOSTIC] Cutscene-related addon detected: '{addonName}' - Event: {type}");

                    // Try to get the addon to see if it's visible and has content
                    var addon = GameGui.GetAddonByName(addonName, 1);
                    if (addon.Address != IntPtr.Zero)
                    {
                        var atkAddon = (AtkUnitBase*)addon.Address;
                        if (atkAddon != null && atkAddon->IsVisible)
                        {
                            Log.Info($"🎬 [DIAGNOSTIC] '{addonName}' is VISIBLE and ACTIVE - This could be our cutscene addon!");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                // Silent fail for diagnostic - don't spam logs with errors
            }
        }

        private class TextHookData
        {
            public string Type { get; set; } = "";
            public string Speaker { get; set; } = "";
            public string Message { get; set; } = "";
            public long Timestamp { get; set; }
            public int ChatType { get; set; }
        }

        // Universal addon detector to identify choice dialog addon names
        private void OnUniversalAddonDetector(AddonEvent type, AddonArgs args)
        {
            try
            {
                // Skip common/noisy addons to avoid spam
                var skipAddons = new[] { "Talk", "TalkSubtitle", "_BattleTalk", "NamePlate", "ChatLog",
                                       "_PartyList", "_ActionBar", "MainCommand", "SystemMenu" };

                if (Array.Exists(skipAddons, addon => addon == args.AddonName))
                    return;

                // Log any new addon that appears, especially ones that might be choice dialogs
                Log.Info($"[ADDON-DETECTOR] {args.AddonName} - {type} event");

                // Special attention to potential choice addons
                if (args.AddonName.Contains("Select") || args.AddonName.Contains("Choice") ||
                    args.AddonName.Contains("String") || args.AddonName.Contains("List"))
                {
                    Log.Info($"[POTENTIAL-CHOICE] {args.AddonName} detected!");
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Error in universal addon detector: {ex.Message}");
            }
        }
    }
}