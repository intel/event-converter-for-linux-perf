#!/bin/bash
set -ex

PERFMON_URL=https://download.01.org/perfmon
DATA_PATH=data
PMU_EVENTS_PATH=perf/arch/x86
FILES=(
  "E-core_TMA_Metrics.csv"
  "TMA_Metrics-full.csv"
  "mapfile.csv"
  "readme.txt"
  "ADL/alderlake_goldencove_core_v1.12.json"
  "ADL/alderlake_gracemont_core_v1.12.json"
  "ADL/alderlake_uncore_v1.12.json"
  "BDW/broadwell_core_v26.json"
  "BDW/broadwell_fp_arith_inst_v26.json"
  "BDW/broadwell_matrix_bit_definitions_v26.json"
  "BDW/broadwell_matrix_v26.json"
  "BDW/broadwell_uncore_v26.json"
  "BDW-DE/broadwellde_core_v7.json"
  "BDW-DE/broadwellde_matrix_bit_definitions_v7.json"
  "BDW-DE/broadwellde_uncore_v7.json"
  "BDX/broadwellx_core_v19.json"
  "BDX/broadwellx_matrix_bit_definitions_v19.json"
  "BDX/broadwellx_matrix_v19.json"
  "BDX/broadwellx_uncore_v19.json"
  "BNL/Bonnell_core_V4.json"
  "CLX/cascadelakex_core_v1.16.json"
  "CLX/cascadelakex_fp_arith_inst_v1.16.json"
  "CLX/cascadelakex_uncore_v1.16.json"
  "CLX/cascadelakex_uncore_v1.16_experimental.json"
  "EHL/elkhartlake_core_v1.03.json"
  "GLM/goldmont_core_v13.json"
  "GLM/goldmont_fp_arith_inst_v13.json"
  "GLM/goldmont_matrix_bit_definitions_v13.json"
  "GLM/goldmont_matrix_v13.json"
  # offcore is missing a json version
  "GLP/goldmontplus_core_v1.01.json"
  "GLP/goldmontplus_fp_arith_inst_v1.01.json"
  "GLP/goldmontplus_matrix_bit_definitions_v1.01.json"
  "GLP/goldmontplus_matrix_v1.01.json"
  # offcore is missing a json version
  "HSW/haswell_core_v30.json"
  "HSW/haswell_matrix_bit_definitions_v30.json"
  "HSW/haswell_matrix_v30.json"
  "HSW/haswell_uncore_v30.json"
  "HSX/haswellx_core_v24.json"
  "HSX/haswellx_matrix_bit_definitions_v24.json"
  "HSX/haswellx_matrix_v24.json"
  "HSX/haswellx_uncore_v24.json"
  "ICL/icelake_core_v1.13.json"
  "ICL/icelake_uncore_v1.13.json"
  "ICX/icelakex_core_v1.14.json"
  "ICX/icelakex_uncore_v1.14.json"
  "ICX/icelakex_uncore_v1.14_experimental.json"
  "IVB/ivybridge_core_v22.json"
  "IVB/ivybridge_fp_arith_inst_v22.json"
  "IVB/ivybridge_matrix_bit_definitions_v22.json"
  "IVB/ivybridge_matrix_v22.json"
  "IVB/ivybridge_uncore_v22.json"
  "IVT/ivytown_core_v21.json"
  "IVT/ivytown_matrix_bit_definitions_v21.json"
  "IVT/ivytown_matrix_v21.json"
  "IVT/ivytown_uncore_v21.json"
  "JKT/Jaketown_core_V21.json"
  "JKT/Jaketown_matrix_V21.json"
  "JKT/Jaketown_matrix_bit_definitions_V21.json"
  "JKT/Jaketown_uncore_V21.json"
  "KNL/KnightsLanding_core_V9.json"
  "KNL/KnightsLanding_matrix_V9.json"
  "KNL/KnightsLanding_matrix_bit_definitions_V9.json"
  "KNL/KnightsLanding_uncore_V9.json"
  "KNM/KnightsLanding_core_V9.json"
  "KNM/KnightsLanding_uncore_V9.json"
  "MTL/meteorlake_crestmont_core_v1.00.json"
  "MTL/meteorlake_redwoodcove_core_v1.00.json"
  "NHM-EP/NehalemEP_core_V3.json"
  "NHM-EX/NehalemEX_core_V3.json"
  "SKL/skylake_core_v53.json"
  "SKL/skylake_fp_arith_inst_v53.json"
  "SKL/skylake_matrix_bit_definitions_v53.json"
  "SKL/skylake_matrix_v53.json"
  "SKL/skylake_uncore_v53.json"
  "SKX/skylakex_core_v1.28.json"
  "SKX/skylakex_fp_arith_inst_v1.28.json"
  "SKX/skylakex_matrix_bit_definitions_v1.28.json"
  "SKX/skylakex_matrix_v1.28.json"
  "SKX/skylakex_uncore_v1.28.json"
  "SKX/skylakex_uncore_v1.28_experimental.json"
  "SLM/Silvermont_core_V14.json"
  "SLM/Silvermont_matrix_V14.json"
  "SNB/sandybridge_core_v17.json"
  "SNB/sandybridge_matrix_bit_definitions_v17.json"
  "SNB/sandybridge_matrix_v17.json"
  "SNB/sandybridge_uncore_v17.json"
  "SNR/snowridgex_core_v1.20.json"
  "SNR/snowridgex_uncore_v1.20.json"
  "SNR/snowridgex_uncore_v1.20_experimental.json"
  "SPR/sapphirerapids_core_v1.03.json"
  "SPR/sapphirerapids_uncore_v1.03.json"
  "SPR/sapphirerapids_uncore_v1.03_experimental.json"
  "TGL/tigerlake_core_v1.07.json"
  "TGL/tigerlake_uncore_v1.07.json"
  "WSM-EP-DP/WestmereEP-DP_core_V2.json"
  "WSM-EP-SP/WestmereEP-SP_core_V3.json"
  "WSM-EX/WestmereEX_core_V3.json"
)

declare -A ARCH_NAMES=(
    ["ADL"]="alderlake"
    ["BDW"]="broadwell"
    ["BDW-DE"]="broadwellde"
    ["BDX"]="broadwellx"
    ["BNL"]="Bonnell"
    ["CLX"]="cascadelakex"
    ["EHL"]="elkhartlake"
    ["GLM"]="goldmont"
    ["GLP"]="goldmontplus"
    ["HSW"]="haswell"
    ["HSX"]="haswellx"
    ["ICL"]="icelake"
    ["ICX"]="icelakex"
    ["IVB"]="ivybridge"
    ["IVT"]="ivytown"
    ["JKT"]="Jaketown"
    ["KNL"]="KnightsLanding"
    ["KNM"]="KnightsLanding"
    ["MTL"]="meteorlake"
    ["NHM-EP"]="NehalemEP"
    ["SKL"]="skylake"
    ["SKX"]="skylakex"
    ["SLM"]="Silvermont"
    ["SNB"]="sandybridge"
    ["SNR"]="tremontx"
    ["SPR"]="sapphirerapids"
    ["TGL"]="tigerlake"
    ["WSM-EP-DP"]="WestmereEP-DP"
    ["WSM-EP-SP"]="WestmereEP-SP"
    ["WSM-EX"]="WestmereEX"
)

declare -A HYBRID_ARCH_NAMES_CORE=(
  ["ADL"]="alderlake_goldencove"
  ["MTL"]="meteorlake_redwoodcove"
)

declare -A HYBRID_ARCH_NAMES_ATOM=(
  ["ADL"]="alderlake_gracemont"
  ["MTL"]="meteorlake_crestmont"
)

declare -A TMA_MODELS=(
  ["BDW"]="BDW"
  ["BDW-DE"]="BDX"
  ["BDX"]="BDX"
  ["CLX"]="CLX"
  ["HSW"]="HSW"
  ["HSX"]="HSX"
  ["ICL"]="ICL"
  ["ICX"]="ICX"
  ["IVB"]="IVB"
  ["IVT"]="IVT"
  ["JKT"]="JKT/SNB-EP"
  ["SKL"]="SKL/KBL"
  ["SKX"]="SKX"
  ["SNB"]="SNB"
  ["SPR"]="SPR"
)

declare -A HYBRID_TMA_MODELS_CORE=(
  ["ADL"]="ADL/RPL"
)

declare -A HYBRID_TMA_MODELS_ATOM=(
  ["ADL"]="GRT"
)

# Download source json files from 01.org
mkdir -p ${DATA_PATH}
for i in "${FILES[@]}"
do
  echo "${PERFMON_URL}/$i"
done | wget -i - -P ${DATA_PATH} -x -nH --cut-dirs=1

# Convert 01.org json to perf json
for short in "${!ARCH_NAMES[@]}"
do
  outdir=${PMU_EVENTS_PATH}/${ARCH_NAMES[$short],,}
  mkdir -p "$outdir"
  if [ `ls -l ${DATA_PATH}/"$short"/*_core_*.json|wc -l` == "1" ]
  then
    python3 json-to-perf-json.py --outdir "$outdir" ${DATA_PATH}/"$short"/*_core_*.json
  else
    python3 hybrid-json-to-perf-json.py \
      ${DATA_PATH}/"$short"/${HYBRID_ARCH_NAMES_ATOM[$short]}_core_*.json \
      ${DATA_PATH}/"$short"/${HYBRID_ARCH_NAMES_CORE[$short]}_core_*.json \
      --outdir "$outdir"
  fi
  if [ -r ./perf-uncore-events-${short,,}.csv ]
  then
    python3 uncore_csv_json.py \
      --all \
      ./perf-uncore-events-${short,,}.csv \
      ${DATA_PATH}/"$short"/*_uncore_[vV]*[^a-z].json \
      "$outdir" \
      $(ls ${DATA_PATH}/"$short"/*_uncore_v*_experimental.json)
  fi
done

# Extract metrics from TMA_Metrics.csv
for short in "${!TMA_MODELS[@]}"
do
  model=${TMA_MODELS[$short]}
  echo "\n\n\nProcessing TMA metrics for $model\n\n\n"
  python3 extract-tma-metrics.py \
    --memory \
    --cstate \
    --expr-events 100 \
    --extramodel \
    "$short" "$model" \
    ${DATA_PATH}/TMA_Metrics-full.csv \
    > ${PMU_EVENTS_PATH}/${ARCH_NAMES[$short],,}/${short,,}-metrics.json
done

# Extract hybrid metrics from TMA_Metrics.csv and E-core-TMA_Metrics.csv
for short in "${!HYBRID_TMA_MODELS_CORE[@]}"
do
  core=${HYBRID_TMA_MODELS_CORE[$short]}
  core_path=${PMU_EVENTS_PATH}/${ARCH_NAMES[$short],,}/${short,,}-core-metrics.json
  atom=${HYBRID_TMA_MODELS_ATOM[$short]}
  atom_path=${PMU_EVENTS_PATH}/${ARCH_NAMES[$short],,}/${short,,}-atom-metrics.json
  echo -e "\\n\\n\\nProcessing hybird core TMA metrics for $core\\n\\n\\n"
  # Note, cstate can only be enabled for 1 of cpu_core or cpu_atom. Here we
  # enable it only for cpu_atom.
  python3 extract-tma-metrics.py \
    --memory \
    --expr-events 100 \
    --unit "cpu_core" \
    --extramodel \
    "$core" "$core" \
    ${DATA_PATH}/TMA_Metrics-full.csv \
    > "$core_path"
  echo -e "\\n\\n\\nProcessing hybird atom TMA metrics for $core\\n\\n\\n"
  python3 extract-tma-metrics.py \
    --memory \
    --cstate \
    --expr-events 100 \
    --unit "cpu_atom" \
    --extramodel \
    "$atom" "$atom" \
    ${DATA_PATH}/E-core_TMA_Metrics.csv \
    > "$atom_path"
  python3 merge-json "$core_path" "$atom_path" \
    > ${PMU_EVENTS_PATH}/${ARCH_NAMES[$short],,}/${short,,}-metrics.json
  rm "$core_path" "$atom_path"
done

# Match perf's path expectation.
mv ${PMU_EVENTS_PATH}/broadwellde/bdw-de-metrics.json \
  ${PMU_EVENTS_PATH}/broadwellde/bdwde-metrics.json

echo SUCCESS!
