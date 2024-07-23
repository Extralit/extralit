

# Check search engine index
index_count=$(python -m argilla_server search-engine list | wc -l)
if [ "$index_count" -le 1 ]; then
    python -m argilla_server search-engine reindex
fi