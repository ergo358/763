import React, { useState, useEffect } from "react";
import { Box, Heading, Text, Button, Input, Table, Thead, Tbody, Tr, Th, Td, useToast } from "@chakra-ui/react";
import axios from "axios";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

export default function App() {
  const [userId, setUserId] = useState("");
  const [room, setRoom] = useState("");
  const [date, setDate] = useState("");
  const [items, setItems] = useState([]);
  const [cancelId, setCancelId] = useState("");
  const toast = useToast();

  const fetchRequests = async () => {
    if (!userId) return;
    const { data } = await axios.get(`${API}/api/requests/${userId}`);
    setItems(data);
  };

  const addRequest = async () => {
    if (!userId || !room || !date) return;
    await axios.post(`${API}/api/requests/add`, null, {
      params: { user_id: userId, username: "web", room, date }
    });
    setRoom(""); setDate("");
    toast({ title: "Заявка добавлена", status: "success" });
    fetchRequests();
  };

  const cancelRequest = async () => {
    await axios.post(`${API}/api/requests/cancel`, null, {
      params: { user_id: userId, request_id: cancelId }
    });
    setCancelId("");
    toast({ title: "Заявка отменена", status: "info" });
    fetchRequests();
  };

  useEffect(() => { fetchRequests(); /* eslint-disable-next-line */ }, [userId]);

  return (
    <Box maxW="600px" mx="auto" p={8}>
      <Heading mb={6}>Бронирование переговорок</Heading>
      <Input placeholder="Ваш Telegram user_id" value={userId} onChange={e => setUserId(e.target.value)} mb={2} />
      <Box display="flex" gap={2} mb={2}>
        <Input placeholder="Переговорка" value={room} onChange={e => setRoom(e.target.value)} />
        <Input placeholder="Дата и время" value={date} onChange={e => setDate(e.target.value)} />
        <Button onClick={addRequest} colorScheme="blue">Добавить</Button>
      </Box>
      <Button onClick={fetchRequests} size="sm" mb={2}>Обновить список</Button>
      <Table size="sm" mb={2}>
        <Thead>
          <Tr>
            <Th>ID</Th>
            <Th>Переговорка</Th>
            <Th>Дата</Th>
            <Th>Статус</Th>
          </Tr>
        </Thead>
        <Tbody>
          {items.map(r =>
            <Tr key={r.id}>
              <Td>{r.id}</Td>
              <Td>{r.room}</Td>
              <Td>{r.date}</Td>
              <Td>{r.status}</Td>
            </Tr>
          )}
        </Tbody>
      </Table>
      <Box display="flex" gap={2} alignItems="center">
        <Input placeholder="ID для отмены" value={cancelId} onChange={e => setCancelId(e.target.value)} w="150px" />
        <Button onClick={cancelRequest} colorScheme="red" size="sm">Отменить</Button>
      </Box>
      <Text mt={6} fontSize="sm">Сначала введите свой user_id (узнать — через /start в боте)</Text>
    </Box>
  );
}