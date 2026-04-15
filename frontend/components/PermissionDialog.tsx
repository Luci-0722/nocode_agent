import React from 'react';
import { Box, Text } from 'ink';
import DialogFrame from './DialogFrame.js';
import { useAppState } from '../hooks/useAppState.js';

export default function PermissionDialog() {
  const { permissionRequest } = useAppState();
  if (!permissionRequest) {
    return null;
  }

  const action = permissionRequest.actions[permissionRequest.actionIndex];
  const approveSelected = permissionRequest.optionIndex === 0;

  return (
    <DialogFrame
      title="Permission Request"
      subtitle={`${permissionRequest.actionIndex + 1}/${permissionRequest.actions.length}`}
    >
      <Text bold>{action.name}</Text>
      {action.description && <Text dimColor>{action.description}</Text>}
      {action.args && (
        <Box flexDirection="column" marginTop={1}>
          <Text dimColor>args</Text>
          <Text>{JSON.stringify(action.args, null, 2)}</Text>
        </Box>
      )}
      <Box marginTop={1}>
        <Text color={approveSelected ? 'cyan' : undefined}>{approveSelected ? '>' : ' '}</Text>
        <Text> Approve</Text>
      </Box>
      <Box>
        <Text color={!approveSelected ? 'cyan' : undefined}>{!approveSelected ? '>' : ' '}</Text>
        <Text> Reject</Text>
      </Box>
    </DialogFrame>
  );
}
