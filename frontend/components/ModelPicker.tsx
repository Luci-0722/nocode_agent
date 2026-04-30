import React from 'react';
import { Box, Text } from 'ink';
import DialogFrame from './DialogFrame.js';
import { useAppState } from '../hooks/useAppState.js';

export default function ModelPicker() {
  const {
    displayRows,
    modelPickerIndex,
    modelName,
    providerFetchResults,
  } = useAppState();

  if (displayRows.length === 0) {
    return (
      <DialogFrame title="Models" subtitle="Up/Down move, Enter select, Ctrl+R refresh, Esc close">
        <Text dimColor>No providers configured.</Text>
      </DialogFrame>
    );
  }

  return (
    <DialogFrame title="Models" subtitle="Up/Down move, Enter select, Ctrl+R refresh, Esc close">
      {displayRows.map((row, index) => {
        if (row.kind === 'header') {
          const result = providerFetchResults[row.provider_name];
          const status = result?.status;
          const hasError = status === 'error';
          const errorMsg = result?.error;

          return (
            <Box key={`h-${row.provider_name}`} flexDirection="column">
              <Box>
                <Text bold dimColor>{row.provider_name}</Text>
                {hasError && <Text color="red"> {`(${errorMsg || 'error'})`}</Text>}
              </Box>
            </Box>
          );
        }

        // Model row
        const selected = index === modelPickerIndex;
        const isCurrent = row.qualified_name === modelName;

        return (
          <Box key={row.qualified_name}>
            <Text color={selected ? 'green' : undefined}>{selected ? '>' : ' '}</Text>
            <Text> </Text>
            <Text bold={selected}>{row.display_name || row.model_id}</Text>
            {isCurrent && <Text color="green"> current</Text>}
          </Box>
        );
      })}
    </DialogFrame>
  );
}
