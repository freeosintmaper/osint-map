#!/usr/bin/env node
"use strict";

// Exercise the actual browser helper functions embedded in index.html with a
// small Leaflet/localStorage/Supabase harness. No network calls are made.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("index.html", "utf8");
const start = html.indexOf("    var USER_ZONES_CACHE_KEY = 'user_control_zones_cache_v1';");
const end = html.indexOf("    loadUserZones(0);", start);
assert.notEqual(start, -1, "author-zone helper block exists");
assert.notEqual(end, -1, "author-zone auto-load call exists");

const memory = new Map();
const layerState = { features: [], clearCalls: 0 };
const userZonesLayer = {
  clearLayers() {
    layerState.clearCalls += 1;
    layerState.features = [];
  },
  addData(feature) {
    layerState.features.push(feature);
  },
  eachLayer(callback) {
    layerState.features.forEach(function(feature) {
      callback({
        _zoneId: feature.properties.id,
        _zoneCategory: feature.properties.category,
        toGeoJSON: function() { return feature; }
      });
    });
  }
};

const sandbox = {
  userZonesLayer,
  localStorage: {
    getItem(key) { return memory.has(key) ? memory.get(key) : null; },
    setItem(key, value) { memory.set(key, String(value)); }
  },
  console: { log() {}, warn() {} },
  fetch() { throw new Error("Unexpected network call in offline test"); },
  setTimeout(fn) { return setTimeout(fn, 0); },
  sb: null
};
vm.createContext(sandbox);
vm.runInContext(html.slice(start, end), sandbox, { filename: "index.html author-zone helpers" });

const validZone = {
  id: 7,
  category: "grey",
  geometry: {
    type: "Polygon",
    coordinates: [[[30, 50], [31, 50], [31, 51], [30, 50]]]
  }
};
const invalidZone = {
  id: 8,
  category: "grey",
  geometry: { type: "Polygon", coordinates: [[[30, 50], [31, 50], [31, 51]]] }
};

async function main() {
  // Valid snapshots render.
  sandbox.renderUserZones([validZone]);
  assert.equal(layerState.features.length, 1);

  // A malformed snapshot is rejected before clearing a working layer.
  const clearCallsBeforeInvalid = layerState.clearCalls;
  assert.throws(() => sandbox.renderUserZones([invalidZone]), /геометрия/);
  assert.equal(layerState.clearCalls, clearCallsBeforeInvalid);
  assert.equal(layerState.features.length, 1);

  // Empty Supabase reads are retried and eventually fall back to the last
  // valid browser cache without replacing that cache or blanking the layer.
  const cacheKey = "user_control_zones_cache_v1";
  const originalCache = JSON.stringify([validZone]);
  memory.set(cacheKey, originalCache);
  let queryCount = 0;
  sandbox.sb = {
    from() {
      return {
        select() {
          queryCount += 1;
          return Promise.resolve({ data: [] });
        }
      };
    }
  };
  sandbox.loadUserZones(0);
  await new Promise(resolve => setTimeout(resolve, 40));
  assert.equal(queryCount, 3, "empty Supabase responses are retried three times");
  assert.equal(memory.get(cacheKey), originalCache, "empty result cannot overwrite known-good cache");
  assert.equal(layerState.features.length, 1, "empty result cannot clear the visible author layer");

  // Cache updates from an empty layer must also preserve the previous snapshot.
  layerState.features = [];
  assert.equal(sandbox.cacheUserZonesFromLayer(), false);
  assert.equal(memory.get(cacheKey), originalCache);

  // A malformed browser cache is rejected without destroying the existing layer.
  memory.set(cacheKey, JSON.stringify([invalidZone]));
  const beforeBadCache = layerState.clearCalls;
  assert.equal(sandbox.loadCachedUserZones(), false);
  assert.equal(layerState.clearCalls, beforeBadCache);

  console.log("Author-zone frontend safety tests passed.");
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
